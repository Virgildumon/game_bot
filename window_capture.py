from ctypes import windll
import numpy as np
import win32gui
import win32ui
import win32con
from global_vars import SCREEN_W, SCREEN_H


class WindowCapture:
    def __init__(self, window_name):
        # find the handle for the window we want to capture
        self.hwnd = win32gui.FindWindow(None, window_name)
        if not self.hwnd:
            raise Exception('Window not found: {}'.format(window_name))

        self.w = SCREEN_W
        self.h = SCREEN_H
        # get the window size
        #window_rect = win32gui.GetWindowRect(self.hwnd)
        #self.w = window_rect[2] - window_rect[0]
        #self.h = window_rect[3] - window_rect[1]

        self.cropped_x = 0
        self.cropped_y = 0
        self.offset_x = 0
        self.offset_y = 0
        """
        # account for the window border and titlebar and cut them off
        border_pixels = 8
        titlebar_pixels = 30
        self.w = self.w - (border_pixels * 2)
        self.h = self.h - titlebar_pixels - border_pixels
        self.cropped_x = border_pixels
        self.cropped_y = titlebar_pixels
        # set the cropped coordinates offset so we can translate screenshot
        # images into actual screen positions
        self.offset_x = window_rect[0] + self.cropped_x
        self.offset_y = window_rect[1] + self.cropped_y
        """

    def get_screenshot(self):
        """
        Get screenshot image (frame) from defined window

        Args:
            self

        Returns:
            np.ndarray | None: screenshot image (frame) or None if error occurred

        Raises:
            None: This function does not raise any specific exceptions.
        """
        try:
            # window must exist and not be minimized, otherwise BitBlt returns black frame
            if not win32gui.IsWindow(self.hwnd):
                print('Exception: window no longer exists')
                return None
            if win32gui.IsIconic(self.hwnd):
                win32gui.ShowWindow(self.hwnd, win32con.SW_RESTORE)
            try:
                win32gui.SetForegroundWindow(self.hwnd)
            except Exception:
                pass

            # get the window image data
            wDC = win32gui.GetWindowDC(self.hwnd)
            dcObj = win32ui.CreateDCFromHandle(wDC)
            cDC = dcObj.CreateCompatibleDC()
            dataBitMap = win32ui.CreateBitmap()
            dataBitMap.CreateCompatibleBitmap(dcObj, self.w, self.h)
            cDC.SelectObject(dataBitMap)

            def grab_to_array():
                signedIntsArray = dataBitMap.GetBitmapBits(True)
                arr = np.fromstring(signedIntsArray, dtype='uint8')
                arr.shape = (self.h, self.w, 4)
                return np.ascontiguousarray(arr)

            img = None
            # method 1: PrintWindow (PW_RENDERFULLCONTENT = 2), works when occluded
            if windll.user32.PrintWindow(self.hwnd, cDC.GetSafeHdc(), 2):
                candidate = grab_to_array()
                if candidate[..., :3].mean() >= 5:
                    img = candidate
            # method 2: BitBlt fallback (or if PrintWindow gave black frame)
            if img is None:
                cDC.BitBlt((0, 0), (self.w, self.h), dcObj, (0, 0), win32con.SRCCOPY)
                candidate = grab_to_array()
                if candidate[..., :3].mean() >= 5:
                    img = candidate

            # free resources
            dcObj.DeleteDC()
            cDC.DeleteDC()
            win32gui.ReleaseDC(self.hwnd, wDC)
            win32gui.DeleteObject(dataBitMap.GetHandle())

            if img is None:
                print('Exception: captured black frame (window occluded or minimized)')
                return None

            # drop the alpha channel, or cv.matchTemplate() will throw an error like:
            #   error: (-215:Assertion failed) (depth == CV_8U || depth == CV_32F) && type == _templ.type()
            #   && _img.dims() <= 2 in function 'cv::matchTemplate'
            #img = img[...,:3]

            return img

        except Exception as e:
            print(f'Exception: {e}')
            return None

        return img

    # translate a pixel position on a screenshot image to a pixel position on the screen.
    # pos = (x, y)
    # WARNING: if you move the window being captured after execution is started, this will
    # return incorrect coordinates, because the window position is only calculated in
    # the __init__ constructor.
    def get_screen_position(self, pos):
        return (pos[0] + self.offset_x, pos[1] + self.offset_y)


def list_window_names():
    """
    find all window's names
    https://stackoverflow.com/questions/55547940/how-to-get-a-list-of-the-name-of-every-open-window
    """
    def winEnumHandler(hwnd, ctx):
        if win32gui.IsWindowVisible(hwnd):
            print(hex(hwnd), win32gui.GetWindowText(hwnd))
    win32gui.EnumWindows(winEnumHandler, None)
