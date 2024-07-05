import ctypes
import os

def test_cuda_init():
    """
    This function attempts to initialize CUDA and returns True if successful, False otherwise.
    """
    cuda_lib = "libcuda.so"
    if os.name == 'nt':  # Windows
        cuda_lib = os.path.join(os.environ.get('SYSTEMROOT'), 'system32', 'nvcuda.dll')
        if not os.path.isfile(cuda_lib):
            cuda_lib = "nvcuda.dll"

    try:
        nvcuda = ctypes.cdll.LoadLibrary(cuda_lib)
        
        nvcuda.cuInit.argtypes = (ctypes.c_uint32,)
        nvcuda.cuInit.restypes = (ctypes.c_int32)
        
        result = nvcuda.cuInit(0)
        
        if result != 0:
            print("CUDA initialization failed with error code:", result)
        if nvcuda.cuInit(0) == 0:
            print("CUDA initialized successfully!")
            return True
        else:
            print("Error initializing CUDA.")
            print(nvcuda.cuInit(0))
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    if test_cuda_init():
        print("CUDA environment seems to be working.")
    else:
        print("CUDA environment is not working. Please check your CUDA installation.")
