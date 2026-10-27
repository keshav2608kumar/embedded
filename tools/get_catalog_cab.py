import urllib.request
import re

url = "https://www.catalog.update.microsoft.com/Search.aspx?q=Silicon%20Laboratories%20CP210x%20Windows%2010"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
html = urllib.request.urlopen(req).read().decode("utf-8", errors="ignore")

matches = re.findall(r'goToDetails\("([a-f0-9\-]+)"\)', html)
print(f"Update IDs: {matches[:3]}")

for uid in matches[:3]:
    post_data = f'updateIDs=[{{"size":0,"languages":"","uidInfo":"{uid}","updateID":"{uid}"}}]'.encode("utf-8")
    d_req = urllib.request.Request(
        "https://www.catalog.update.microsoft.com/DownloadDialog.aspx",
        data=post_data,
        headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/x-www-form-urlencoded"}
    )
    d_html = urllib.request.urlopen(d_req).read().decode("utf-8", errors="ignore")
    urls = re.findall(r"http[s]?://[^\s'\"<>]+\.cab", d_html)
    if urls:
        print(f"UID {uid} CAB: {urls[0]}")
        # Download and extract the CAB file
        cab_url = urls[0]
        cab_dest = r"C:\Users\kesha\Downloads\CP210x_Catalog.cab"
        urllib.request.urlretrieve(cab_url, cab_dest)
        print(f"Successfully downloaded official Windows Update CAB to {cab_dest}!")
        break
