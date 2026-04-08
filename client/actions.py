import pyautogui

screen_w, screen_h = pyautogui.size()

def move_mouse(x, y):
    pyautogui.moveTo(x, y)

def click():
    pyautogui.click()

def scroll_up():
    pyautogui.scroll(50)

def scroll_down():
    pyautogui.scroll(-50)

def zoom_in():
    pyautogui.hotkey('ctrl', '+')

def zoom_out():
    pyautogui.hotkey('ctrl', '-')

def lock_screen():
    pyautogui.hotkey('win', 'l')