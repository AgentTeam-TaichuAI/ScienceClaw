# Obsidian Host Bridge 使用说明

`host_bridge/obsidian_host_bridge.py` 是跑在 Windows 宿主机上的本地桥服务。
它负责两类事情：

1. 让容器内的 agent 把笔记写回宿主机上的 Obsidian vault。
2. 在白名单范围内，读取宿主机上的 PDF / HTML / TXT 附件并回传给容器。

如果桥能启动，但 `paper_evidence` 里出现：

```text
SC_HOST_READ_ROOTS is not configured on the host bridge
```

说明桥服务本身在线，但没有给它配置“允许读取的宿主机目录白名单”，所以 `/host/read-file` 会拒绝读取你的 Zotero 附件。

## 关键点

- `SC_HOST_READ_ROOTS` 必须配置在**宿主机桥进程**上，不是在容器里配。
- 没有白名单时，桥仍然可以写 Obsidian，但不会放行宿主机 PDF/HTML/TXT 的读取。
- 允许的后缀目前是：`.pdf`、`.html`、`.htm`、`.txt`。
- 传给桥的路径必须是宿主机绝对路径，并且落在 `SC_HOST_READ_ROOTS` 里的某个根目录下面。

## 启动方式

默认启动：

```powershell
powershell -ExecutionPolicy Bypass -File .\host_bridge\start_obsidian_host_bridge.ps1
```

带 Zotero 附件白名单启动：

```powershell
powershell -ExecutionPolicy Bypass -File .\host_bridge\start_obsidian_host_bridge.ps1 `
  -PythonExe python `
  -Port 8765 `
  -HostReadRoots 'D:\zotero', 'C:\Users\HK\Zotero\storage'
```

如果你的附件实际放在别的目录，比如项目同步目录，也可以一起加进去：

```powershell
powershell -ExecutionPolicy Bypass -File .\host_bridge\start_obsidian_host_bridge.ps1 `
  -PythonExe python `
  -Port 8765 `
  -HostReadRoots 'D:\zotero', 'C:\Users\HK\Zotero\storage', 'D:\XJTU\ImportantFile\automation\ScienceClaw\zotero'
```

启动时如果配置成功，控制台会打印：

```text
SC_HOST_READ_ROOTS: D:\zotero;C:\Users\HK\Zotero\storage
```

如果没有配置，会看到警告：

```text
SC_HOST_READ_ROOTS is not set. Host-side PDF/HTML attachment reads will be rejected.
```

## 快速自测

1. 先启动桥，并带上 `-HostReadRoots`。
2. 用下面命令检查健康状态：

```powershell
Invoke-RestMethod -Uri 'http://127.0.0.1:8765/health'
```

3. 再测一条实际文件读取：

```powershell
$headers = @{ 'X-Bridge-Token' = 'scienceclaw-local-bridge' }
$body = @{ path = 'C:\Users\HK\Zotero\storage\ABC123\paper.pdf' } | ConvertTo-Json

Invoke-RestMethod `
  -Uri 'http://127.0.0.1:8765/host/read-file' `
  -Method Post `
  -Headers $headers `
  -ContentType 'application/json' `
  -Body $body
```

返回里如果有这些字段，就说明桥已成功读到宿主机文件：

- `ok: true`
- `size`
- `mime_type`
- `content_base64`

如果文件路径不在白名单下，会返回类似：

```text
path is outside allowed host read roots
```

如果根本没配置白名单，会返回：

```text
SC_HOST_READ_ROOTS is not configured on the host bridge
```

## ScienceClaw / Zotero 联动建议

常见的 Zotero 附件目录有两类：

- Zotero 原生存储目录：`C:\Users\HK\Zotero\storage`
- 你自行整理或同步出来的 PDF 根目录：例如 `D:\zotero`

如果 Better BibTeX JSON 里的 `attachments[].path` 混用了这两类目录，建议两者都加入 `-HostReadRoots`。

## 故障排查

1. 桥健康检查正常，但全文仍读不到：
   先看返回错误是不是白名单问题；大多数情况下都是 `SC_HOST_READ_ROOTS` 没配，或者附件路径不在白名单里。
2. 容器里还是走到了旧桥：
   确认你重启的是宿主机上的桥进程，而不是只改了环境变量但没重启服务。
3. 路径存在但仍失败：
   检查 JSON 里记录的是不是宿主机真实路径，尤其注意盘符、空格、中文文件名和同步目录迁移后的旧路径。
4. 想临时放开多个目录：
   直接把多个根目录都传给 `-HostReadRoots`，脚本会自动拼成 `SC_HOST_READ_ROOTS`。
