import zipfile
import io
import tempfile
import os
import shutil
import xarray as xr
import threading
from src.config import TMP_CLEANUP_MANIFEST, MAX_IN_MEMORY_BYTES

_HDF5_OPEN_LOCK = threading.Lock()
# 全局锁，用于序列化 HDF5/netCDF 的打开操作（在导入时初始化以避免延迟竞争）
# 缓存每个驱动器根下用于 ASCII 临时目录的路径，以避免创建/删除大量小目录
# 键：驱动器根字符串（例如 'C:\\'）或表示系统临时的 'system'
_ASCII_TMP_ROOTS = {}

# 全局开关：启用纯内存模式。当为 True 时，严格禁止生成任何临时文件或解压到磁盘。
# 可通过环境变量 PREPROCESS_PURE_MEMORY=1 启用，或者在运行时通过 set_pure_memory(True) 开启。
USE_PURE_MEMORY = os.environ.get('PREPROCESS_PURE_MEMORY', '') == '1'


def set_pure_memory(enabled: bool):
    """运行时切换纯内存模式（仅影响当前进程）。

    enabled=True 时禁止写盘回退与临时文件创建；enabled=False 恢复为环境变量/默认行为。
    """
    global USE_PURE_MEMORY
    USE_PURE_MEMORY = bool(enabled)

def _read_cleanup_manifest():
    try:
        if os.path.exists(TMP_CLEANUP_MANIFEST):
            import json
            with open(TMP_CLEANUP_MANIFEST, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
    except Exception:
        pass
    return []


def _write_cleanup_manifest(lst):
    try:
        import json
        with open(TMP_CLEANUP_MANIFEST, 'w', encoding='utf-8') as f:
            json.dump(lst, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def record_tmp_dir(tmp_dir):
    if not tmp_dir:
        return
    lst = _read_cleanup_manifest()
    if tmp_dir not in lst:
        lst.append(tmp_dir)
        _write_cleanup_manifest(lst)


def cleanup_tmp_dirs(batch_size=10):
    lst = _read_cleanup_manifest()
    deleted = []
    failed = []
    to_do = lst[:batch_size]
    for d in to_do:
        try:
            shutil.rmtree(d)
            deleted.append(d)
        except Exception:
            failed.append(d)

    remaining = [d for d in lst if d not in deleted]
    _write_cleanup_manifest(remaining)
    return deleted, failed


def _available_backends():
    info = {}
    try:
        import netCDF4  
        info['netCDF4'] = True
    except Exception:
        info['netCDF4'] = False
    try:
        import h5netcdf  
        info['h5netcdf'] = True
    except Exception:
        info['h5netcdf'] = False
    try:
        import h5py  
        info['h5py'] = True
    except Exception:
        info['h5py'] = False
    return info


def _try_open_with_engines(nc_path, engines=None):
    def _get_supported_engine_names():
        try:
            info = xr.backends.list_engines()
            names = set()
            if isinstance(info, dict):
                for v in info.values():
                    if isinstance(v, (list, tuple)):
                        names.update(v)
            return names
        except Exception:
            return set()

    supported = _get_supported_engine_names()

    if engines is None:
        candidates = [None]
        for e in ['netcdf4', 'h5netcdf', 'h5py', 'scipy']:
            if e in supported:
                candidates.append(e)
    else:
        candidates = []
        for e in engines:
            if e is None or e in supported:
                candidates.append(e)
        if not candidates:
            candidates = [None]

    last_exc = None
    # HDF5 及部分后端并非完全线程安全；对实际的打开调用进行序列化
    # 可以避免在 Windows 上出现来自底层 C 库的无效句柄/标识符错误。
    # 使用在模块导入时初始化的全局锁 _HDF5_OPEN_LOCK。

    for eng in candidates:
        try:
            with _HDF5_OPEN_LOCK:
                if eng is None:
                    ds = xr.open_dataset(nc_path)
                else:
                    ds = xr.open_dataset(nc_path, engine=eng)
            return ds
        except Exception as e:
            last_exc = e
    raise last_exc


def read_nc_from_zip(zip_file_path, nc_file_name=None):
    """Robustly read a single .nc member from a zip.
    Returns (xarray.Dataset, tmp_dir_or_none). Caller must close ds and delete tmp dir or record for cleanup.
    """
    if not os.path.exists(zip_file_path):
        raise FileNotFoundError(zip_file_path)

    # debug toggled by environment variable PREPROCESS_DEBUG=1
        # 调试开关由环境变量 PREPROCESS_DEBUG=1 控制
    _debug = os.environ.get('PREPROCESS_DEBUG', '') == '1'
    # force disk extraction (skip in-memory) if PREPROCESS_FORCE_DISK=1
    # 不再在 Windows 上默认强制使用磁盘解压；改为优先尝试内存打开。
    _force_disk = os.environ.get('PREPROCESS_FORCE_DISK', '') == '1'
    # 如果内存打开失败且需要回退到磁盘解压，设置 PREPROCESS_ALLOW_DISK_FALLBACK=1
    # 默认情况下（未设置），尽量不写入磁盘以节省空间。
    _allow_disk_fallback = os.environ.get('PREPROCESS_ALLOW_DISK_FALLBACK', '') == '1'
    if _debug:
        try:
            print(f"[io_utils] read_nc_from_zip start: {zip_file_path}, member={nc_file_name}")
        except Exception:
            pass

    with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
        if nc_file_name is None:
            nc_files = [f for f in zip_ref.namelist() if f.endswith('.nc')]
            if not nc_files:
                raise ValueError(f"在 {zip_file_path} 中未找到NC文件")
            nc_file_name = nc_files[0]

        try:
            with zip_ref.open(nc_file_name) as file_in_zip:
                try:
                    info = zip_ref.getinfo(nc_file_name)
                    file_size = info.file_size
                except Exception:
                    file_size = None

                try_in_memory = (file_size is None) or (file_size <= MAX_IN_MEMORY_BYTES)
                if _force_disk:
                    if _debug:
                        print(f"[io_utils] PREPROCESS_FORCE_DISK enabled; skipping in-memory path for {nc_file_name}")
                    try_in_memory = False
                else:
                    # 仅在存在支持文件类对象的 engine 时才尝试内存打开
                    try:
                        supported = set()
                        try:
                            info = xr.backends.list_engines()
                            if isinstance(info, dict):
                                for v in info.values():
                                    if isinstance(v, (list, tuple)):
                                        supported.update(v)
                        except Exception:
                            supported = set()
                        if _debug:
                            print(f"[io_utils] supported engines: {supported}")
                        filelike_engines = {'h5netcdf', 'scipy'}
                        if not (filelike_engines & supported):
                            if _debug:
                                print(f"[io_utils] no file-like-supporting engines available; skipping in-memory for {nc_file_name}")
                                if _debug:
                                    print(f"[io_utils] 未检测到支持 file-like 的 engine；对 {nc_file_name} 跳过内存打开")
                            try_in_memory = False
                    except Exception:
                        # if detection fails, be conservative and skip in-memory
                        try_in_memory = False

                if _debug:
                    print(f"[io_utils] candidate member '{nc_file_name}' size={file_size} try_in_memory={try_in_memory}")

                # 尽量在内存中打开，避免解压到磁盘。
                # 优先尝试对字节流使用不依赖 HDF5 C 库的后端（按顺序尝试 'h5netcdf', 'scipy'），
                # 如果这些都不可用再作为最后手段尝试 netCDF4 的 memory 模式。
                attempted_inmemory = False
                if try_in_memory and (not _force_disk):
                    try:
                        nc_bytes = file_in_zip.read()
                    except Exception:
                        nc_bytes = None

                    if nc_bytes is not None and (MAX_IN_MEMORY_BYTES is None or len(nc_bytes) <= MAX_IN_MEMORY_BYTES):
                        if _debug:
                            print(f"[io_utils] attempting in-memory open for {nc_file_name} (bytes={len(nc_bytes)})")

                        # 优先尝试的引擎列表（用户要求只用 h5netcdf 和 scipy）
                        preferred = ['h5netcdf', 'scipy']
                        try:
                            info = xr.backends.list_engines()
                            supported = set()
                            if isinstance(info, dict):
                                for v in info.values():
                                    if isinstance(v, (list, tuple)):
                                        supported.update(v)
                        except Exception:
                            supported = set()

                        engines = [e for e in preferred if e in supported]
                        for eng in engines:
                            try:
                                bio = io.BytesIO(nc_bytes)
                                with _HDF5_OPEN_LOCK:
                                    ds = xr.open_dataset(bio, engine=eng)
                                if _debug:
                                    print(f"[io_utils] in-memory open succeeded for {nc_file_name} using engine={eng}")
                                attempted_inmemory = True
                                return ds, None
                            except Exception as e_mem:
                                if _debug:
                                    print(f"[io_utils] in-memory open with engine={eng} failed: {e_mem}")

                        # 最后尝试 netCDF4 memory（若用户装了 netCDF4）作为兼容后备，但尽量避免依赖它
                        try:
                            import netCDF4
                            try:
                                nc4 = netCDF4.Dataset('inmemory', mode='r', memory=nc_bytes)
                                try:
                                    from xarray.backends import NetCDF4DataStore
                                    xr_ds = xr.open_dataset(NetCDF4DataStore(nc4))
                                except Exception:
                                    xr_ds = xr.open_dataset(nc4)
                                if _debug:
                                    print(f"[io_utils] in-memory open succeeded for {nc_file_name} using netCDF4 memory")
                                attempted_inmemory = True
                                return xr_ds, None
                            except Exception:
                                try:
                                    nc4.close()
                                except Exception:
                                    pass
                        except Exception:
                            # netCDF4 不可用或失败 -> 继续
                            pass
                    else:
                        if _debug:
                            print(f"[io_utils] 无法读取或文件过大，size={None if nc_bytes is None else len(nc_bytes)}; try_in_memory={try_in_memory}")
                else:
                    if _debug:
                        print(f"[io_utils] 未尝试内存打开 (try_in_memory={try_in_memory}, force_disk={_force_disk})")

                # 如果内存打开失败且不允许回退到磁盘，则抛出错误以避免写盘
                if not attempted_inmemory and (not _allow_disk_fallback):
                    raise RuntimeError(f"内存打开 {nc_file_name} 失败，且未设置 PREPROCESS_ALLOW_DISK_FALLBACK=1；为避免写入磁盘已停止。")
        except Exception:
            pass

        try:
            tmp_base = os.path.dirname(os.path.abspath(zip_file_path)) or None
        except Exception:
            tmp_base = None

        if tmp_base:
            try:
                tmp_dir = tempfile.mkdtemp(dir=tmp_base)
            except Exception:
                tmp_dir = tempfile.mkdtemp()
        else:
            tmp_dir = tempfile.mkdtemp()

        try:
            try:
                # 手动按平铺的文件名（basename）解压，避免 zip 成员中的目录前缀或解压 quirks
                # 导致返回路径不可预期或不存在。
                if _debug:
                    print(f"[io_utils] manually extracting {nc_file_name} to tmp dir {tmp_dir}")
                target_name = os.path.basename(nc_file_name) or nc_file_name.replace('/', '_').replace('\\', '_')
                extracted_path = os.path.join(tmp_dir, target_name)
                try:
                    with zip_ref.open(nc_file_name) as src, open(extracted_path, 'wb') as dst:
                        shutil.copyfileobj(src, dst)
                except Exception as e:
                    # fallback to zip_ref.extract if manual copy fails for some reason
                    if _debug:
                        print(f"[io_utils] manual copy failed: {e}; falling back to zip_ref.extract")
                    extracted_path = zip_ref.extract(nc_file_name, path=tmp_dir)

                if _debug:
                    print(f"[io_utils] extraction complete: {extracted_path}")
                    try:
                        exists = os.path.exists(extracted_path)
                        print(f"[io_utils] extracted_path exists: {exists}")
                    except Exception:
                        pass
                    try:
                        print(f"[io_utils] tmp_dir listing: {os.listdir(tmp_dir)}")
                    except Exception:
                        pass
                    try:
                        st = os.stat(extracted_path)
                        print(f"[io_utils] extracted file stat: size={st.st_size} mode={st.st_mode}")
                    except Exception as e:
                        print(f"[io_utils] stat failed on extracted_path: {e}")

                # 验证解压后的文件能被立即打开。有些环境（杀毒/网络文件系统）可能会移除或锁定文件；
                # 如果不能打开，则重试并/或回退到系统临时目录。
                open_ok = False
                try:
                    with open(extracted_path, 'rb') as fh:
                        fh.read(8)
                    open_ok = True
                    if _debug:
                        print(f"[io_utils] verified open of extracted file: {extracted_path}")
                except Exception as oe:
                    if _debug:
                        print(f"[io_utils] could not open extracted file: {oe}")

                if not open_ok:
                    # 重试：从 zip 成员写入到系统临时目录的文件
                    try:
                        sys_tmp = tempfile.mkdtemp()
                        fallback_path = os.path.join(sys_tmp, os.path.basename(nc_file_name))
                        if _debug:
                            print(f"[io_utils] attempting fallback extraction to system tmp: {fallback_path}")
                        with zip_ref.open(nc_file_name) as src, open(fallback_path, 'wb') as dst:
                            shutil.copyfileobj(src, dst)
                        if _debug:
                            print(f"[io_utils] fallback extraction complete: {fallback_path}")
                        # replace extracted_path and tmp_dir
                        extracted_path = fallback_path
                        tmp_dir = sys_tmp
                        open_ok = True
                    except Exception as fe:
                        if _debug:
                            print(f"[io_utils] fallback extraction failed: {fe}")
                        # let the subsequent open attempt fail and be handled below
            except Exception as e:
                if _debug:
                    print(f"[io_utils] extract failed: {e}")
                raise RuntimeError(f"解压 {nc_file_name} 到临时目录 {tmp_dir} 时失败: {e}") from e

            engines = ['netcdf4', 'h5netcdf', 'scipy']
            try:
                if _debug:
                    print(f"[io_utils] attempting to open extracted file with engines: {engines}")
                ds = _try_open_with_engines(extracted_path, engines=engines)
                if _debug:
                    print(f"[io_utils] opened extracted file successfully: {extracted_path}")

                # Try to eagerly load into memory and remove temp files immediately
                try:
                    file_size_known = None
                    try:
                        file_size_known = info.file_size if 'info' in locals() and getattr(info, 'file_size', None) else None
                    except Exception:
                        file_size_known = None
                    try:
                        if file_size_known is None and os.path.exists(extracted_path):
                            file_size_known = os.path.getsize(extracted_path)
                    except Exception:
                        file_size_known = None

                    should_eager_load = False
                    try:
                        if MAX_IN_MEMORY_BYTES is None:
                            should_eager_load = True
                        elif file_size_known is not None and file_size_known <= MAX_IN_MEMORY_BYTES:
                            should_eager_load = True
                    except Exception:
                        should_eager_load = False

                    if should_eager_load:
                        if _debug:
                            print(f"[io_utils] eager-loading dataset into memory (size={file_size_known}) and removing tmp dir {tmp_dir}")
                        try:
                            # load all data into memory-backed arrays
                            ds_loaded = ds.load()
                            try:
                                ds.close()
                            except Exception:
                                pass
                            # attempt to remove tmp_dir immediately
                            try:
                                if tmp_dir:
                                    shutil.rmtree(tmp_dir)
                            except Exception:
                                # record for later cleanup if removal fails
                                try:
                                    record_tmp_dir(tmp_dir)
                                except Exception:
                                    pass
                            return ds_loaded, None
                        except Exception as e_load:
                            if _debug:
                                print(f"[io_utils] eager load failed: {e_load}; returning on-disk dataset and tmp_dir")
                            # fallthrough to return original ds and tmp_dir

                except Exception:
                    # any error deciding eager-load -> keep original behavior
                    pass

                return ds, tmp_dir
            except Exception as final_exc:
                # 如果打开失败并出现底层 C 层的“文件不存在”错误（常见于路径包含非 ASCII 或 HDF5 后端
                # 无法访问文件时），尝试将解压出的文件复制到同一驱动器根下的短 ASCII 路径并从那里重试打开。
                if _debug:
                    print(f"[io_utils] opening extracted file failed: {final_exc}")
                should_retry = False
                try:
                    import errno
                    if isinstance(final_exc, FileNotFoundError):
                        should_retry = True
                    else:
                        msg = str(final_exc).lower()
                        if 'no such file' in msg or 'cannot open' in msg or 'cannot find' in msg:
                            should_retry = True
                except Exception:
                    should_retry = False

                if should_retry:
                    try:
                        # determine drive root from the original zip path (prefer same drive)
                        drive = os.path.splitdrive(zip_file_path)[0]
                        if not drive:
                            drive = os.path.splitdrive(extracted_path)[0]
                        # fallback to system temp if drive not found
                        if not drive:
                            drive_root = None
                        else:
                            drive_root = drive + os.sep
                        # 为该驱动器根复用或创建一个稳定的 ASCII 临时目录
                        try:
                            key = (drive_root if drive_root else 'system')
                            existing = _ASCII_TMP_ROOTS.get(key)
                            if existing and os.path.isdir(existing):
                                ascii_tmp = existing
                            else:
                                from uuid import uuid4
                                if drive_root:
                                    ascii_tmp = os.path.join(drive_root, f"tmp_io_utils_{uuid4().hex}")
                                    try:
                                        os.makedirs(ascii_tmp, exist_ok=True)
                                    except Exception:
                                        ascii_tmp = tempfile.mkdtemp()
                                else:
                                    ascii_tmp = tempfile.mkdtemp()
                                _ASCII_TMP_ROOTS[key] = ascii_tmp
                        except Exception:
                            ascii_tmp = tempfile.mkdtemp()

                        fallback_path = os.path.join(ascii_tmp, os.path.basename(extracted_path))
                        if _debug:
                            print(f"[io_utils] attempting retry by copying to ASCII path: {fallback_path}")
                        try:
                            shutil.copy2(extracted_path, fallback_path)
                            if _debug:
                                print(f"[io_utils] copy to ascii tmp completed, stat={os.stat(fallback_path).st_size}")
                            ds = _try_open_with_engines(fallback_path, engines=engines)
                            if _debug:
                                print(f"[io_utils] opened extracted file successfully from fallback: {fallback_path}")
                            # 对回退复制的文件也尝试 eager-load
                            try:
                                file_size_known_fb = None
                                try:
                                    file_size_known_fb = os.path.getsize(fallback_path)
                                except Exception:
                                    file_size_known_fb = None
                                if file_size_known_fb is not None and (MAX_IN_MEMORY_BYTES is None or file_size_known_fb <= MAX_IN_MEMORY_BYTES):
                                    try:
                                        ds_loaded_fb = ds.load()
                                        try:
                                            ds.close()
                                        except Exception:
                                            pass
                                        try:
                                            shutil.rmtree(ascii_tmp)
                                        except Exception:
                                            try:
                                                record_tmp_dir(ascii_tmp)
                                            except Exception:
                                                pass
                                        return ds_loaded_fb, None
                                    except Exception:
                                        # fall back to returning on-disk ds
                                        pass
                            except Exception:
                                pass
                            return ds, ascii_tmp
                        except Exception as re:
                            if _debug:
                                print(f"[io_utils] retry open from ascii path failed: {re}")
                    except Exception as rx:
                        if _debug:
                            print(f"[io_utils] retry logic failed: {rx}")

                backends_info = _available_backends()
                msg_lines = [
                    f"无法用这些 engine 打开 {nc_file_name}: {', '.join(engines)}",
                    f"最后的错误: {final_exc}",
                    "已检测到的可选后端模块: " + ', '.join([f"{k}={'OK' if v else 'MISSING'}" for k, v in backends_info.items()]),
                ]
                try:
                    shutil.rmtree(tmp_dir)
                except Exception:
                    pass
                raise RuntimeError('\n'.join(msg_lines)) from final_exc
        finally:
            if _debug:
                try:
                    print(f"[io_utils] read_nc_from_zip end (no success) for {zip_file_path}")
                except Exception:
                    pass

def read_nc_bytes(zip_path: str, nc_file_name: str = None) -> bytes:
    """
    从 ZIP 文件中安全地读取指定的 .nc 成员到内存（不落地），返回 bytes。

    参数:
      zip_path: ZIP 文件路径
      nc_file_name: 可选，ZIP 内的成员名（例如 'folder/file.nc'）。
                    若为 None，则读取第一个以 .nc 结尾的成员。

    返回:
      bytes 内容

    注意: 本函数不会在磁盘创建任何临时文件。
    """
    with zipfile.ZipFile(zip_path, 'r') as zf:
        if nc_file_name is None:
            nc_names = [n for n in zf.namelist() if n.endswith('.nc')]
            if not nc_names:
                raise FileNotFoundError(f"No .nc found in {zip_path}")
            nc_file_name = nc_names[0]

        # 以只读模式打开成员并返回全部字节；不做任何落地写入
        with zf.open(nc_file_name, 'r') as nc_file:
            return nc_file.read()