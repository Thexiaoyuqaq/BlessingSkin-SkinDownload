# BlessingSkin Crawler 🎨

一个用于批量爬取 [BlessingSkin](https://skin.prinzeugen.net/) 皮肤数据并下载对应材质图片的 Python 爬虫工具。
注： littleskin同样使用了BlessingSkin框架，也可以使用，只需在main.py更换域名地址

## ✨ 特性

- 🚀 **批量爬取**: 支持指定 ID 范围批量获取皮肤数据
- ⚡ **多线程下载**: 使用线程池提高下载效率
- 🔄 **智能重试**: 网络异常时自动重试，提高成功率
- 📁 **自动分类**: 按皮肤类型自动分类保存（skins/capes/others）
- 🎯 **去重处理**: 避免重复下载已存在的文件
- 📊 **实时进度**: 显示详细的下载进度和统计信息
- 📝 **完整日志**: 记录详细的操作日志便于排查问题
- ⏸️ **优雅中断**: 支持 Ctrl+C 安全中断程序

## 🛠️ 安装

### 环境要求

- Python 3.6+
- requests 库

### 安装依赖

```bash
pip install requests
```

## 🚀 使用方法

### 基本使用

1. 克隆仓库：
```bash
git clone https://github.com/yourusername/littleskin-crawler.git
cd littleskin-crawler
```

2. 运行爬虫：
```bash
python main.py
```

3. 按提示输入参数：
```
请输入起始ID: 1
请输入结束ID: 1000
将处理 1000 个ID (从 1 到 1000)
确认开始爬取？(y/N): y
```

### 示例输出

```
LittleSkin皮肤爬虫脚本
==================================================
将处理 1000 个ID (从 1 到 1000)
确认开始爬取？(y/N): y

开始处理，使用 5 个并发线程...
--------------------------------------------------
2025-08-09 20:06:02,854 - INFO - ID 5000: 下载成功 - Sincere丶low_steve.png (1382 bytes)
2025-08-09 20:06:04,057 - INFO - ID 5005: 下载成功 - 580_steve.png (2519 bytes)
进度: 856/1000 (85.6%) - 成功: 432, 失败: 424

爬取完成!
==================================================
总计处理: 1000
成功下载: 432
失败数量: 568
成功率: 43.2%
文件保存在: ./imgs
```

## 📁 文件结构

爬取的文件会按以下结构自动组织：

```
imgs/
├── skins/              # Steve/Alex 类型皮肤
│   ├── player_steve.png
│   └── custom_alex.png
├── capes/              # 披风材质
│   ├── cape_001.png
│   └── special_cape.png
└── others/             # 其他类型材质
    └── unknown_type.png
```

## ⚙️ 配置选项

可以通过修改脚本顶部的常量来调整行为：

```python
MAX_WORKERS = 5         # 并发下载线程数
RETRY_COUNT = 3         # 网络失败重试次数
REQUEST_DELAY = 0.5     # 请求间隔（秒）
```

## 📊 API 数据结构

BlessingSkin API 返回的数据格式：

```json
{
    "tid": 33,
    "name": "101670",
    "type": "cape",
    "hash": "4ca94a738a9b8c08be6f0a5ff75e469cd66c73e64b50e80507c9b89af8bcce37",
    "size": 95,
    "uploader": 53,
    "public": true,
    "upload_at": "2017-08-16 23:42:27",
    "likes": 46
}
```

## 🔧 高级用法

### 自定义下载路径

修改 `IMGS_FOLDER` 变量：

```python
IMGS_FOLDER = "my_skins"  # 自定义文件夹名
```

### 调整并发数

根据网络状况和服务器负载调整：

```python
MAX_WORKERS = 10  # 增加并发数（请谨慎使用）
```

### 增加请求延迟

为了更好地遵守网站规则：

```python
REQUEST_DELAY = 1.0  # 增加到1秒间隔
```

## 📝 日志文件

程序会生成 `crawler.log` 日志文件，包含：

- 详细的下载进度信息
- 错误和警告信息
- 网络请求状态
- 文件操作结果

## ⚠️ 注意事项

1. **请遵守网站使用条款**：合理控制爬取频率，避免给服务器造成过大压力
2. **网络稳定性**：建议在网络状况良好时使用，避免频繁的重试
3. **存储空间**：确保有足够的磁盘空间存储下载的图片
4. **版权声明**：下载的皮肤文件仅供个人学习使用，请尊重原作者版权

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📜 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 鸣谢

- [BlessingSkin](https://skin.prinzeugen.net/) - 提供优秀的皮肤分享平台
- [requests](https://docs.python-requests.org/) - 优秀的 HTTP 库

## 📞 联系方式

如有问题或建议，请通过以下方式联系：

- 提交 GitHub Issue
- 发送邮件至：xiaoyu@xyqaq.xyz
---

⭐ 如果这个项目对你有帮助，请给个 Star 支持一下！
