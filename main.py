#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests
import json
import os
import time
import sys
from urllib.parse import urljoin
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# 配置
LITTLESKIN_API_URL = "https://littleskin.cn/texture/{}"
SKIN_DOWNLOAD_URL = "https://littleskin.cn/textures/{}"
IMGS_FOLDER = "imgs"
MAX_WORKERS = 5  # 并发下载线程数
RETRY_COUNT = 3  # 重试次数
REQUEST_DELAY = 0.5  # 请求间隔（秒）

print_lock = Lock()

def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('crawler.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

def create_dirs():
    if not os.path.exists(IMGS_FOLDER):
        os.makedirs(IMGS_FOLDER)
        logger.info(f"创建文件夹: {IMGS_FOLDER}")

def get_texture_info(texture_id):
    """
    获取指定ID的皮肤信息
    
    Args:
        texture_id (int): 皮肤ID
        
    Returns:
        dict or None: 皮肤信息字典，失败返回None
    """
    url = LITTLESKIN_API_URL.format(texture_id)
    
    for attempt in range(RETRY_COUNT):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Referer': 'https://littleskin.cn/'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    return data
                except json.JSONDecodeError:
                    logger.warning(f"ID {texture_id}: JSON解析失败")
                    return None
            elif response.status_code == 404:
                logger.debug(f"ID {texture_id}: 不存在")
                return None
            else:
                logger.warning(f"ID {texture_id}: HTTP {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            logger.warning(f"ID {texture_id} 请求失败 (尝试 {attempt + 1}/{RETRY_COUNT}): {e}")
            
        if attempt < RETRY_COUNT - 1:
            time.sleep(1)
    
    return None

def download_texture_image(texture_hash, texture_name, texture_type, texture_id):
    """
    下载皮肤图片
    
    Args:
        texture_hash (str): 皮肤哈希值
        texture_name (str): 皮肤名称
        texture_type (str): 皮肤类型 (steve/alex/cape)
        texture_id (int): 皮肤ID
        
    Returns:
        bool: 下载成功返回True，失败返回False
    """
    url = SKIN_DOWNLOAD_URL.format(texture_hash)
    
    # 根据类型确定文件扩展名和文件夹
    if texture_type in ['steve', 'alex']:
        file_ext = 'png'
        subfolder = 'skins'
    elif texture_type == 'cape':
        file_ext = 'png'
        subfolder = 'capes'
    else:
        file_ext = 'png'
        subfolder = 'others'
    
    save_dir = os.path.join(IMGS_FOLDER, subfolder)
    if not os.path.exists(save_dir):
        os.makedirs(save_dir, exist_ok=True)
    
    if texture_name and texture_name.strip():
        filename = f"{texture_name}_{texture_type}.{file_ext}"
    else:
        filename = f"{texture_id}_{texture_hash[:8]}.{file_ext}"
    
    filename = "".join(c for c in filename if c.isalnum() or c in "._-")
    filepath = os.path.join(save_dir, filename)
    
    if os.path.exists(filepath):
        with print_lock:
            logger.info(f"ID {texture_id}: 文件已存在，跳过下载 - {filename}")
        return True
    
    for attempt in range(RETRY_COUNT):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': 'https://littleskin.cn/'
            }
            
            response = requests.get(url, headers=headers, timeout=30, stream=True)
            
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '').lower()
                if 'image' not in content_type:
                    logger.warning(f"ID {texture_id}: 下载的不是图片文件 (Content-Type: {content_type})")
                    return False
                
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                file_size = os.path.getsize(filepath)
                if file_size > 0:
                    with print_lock:
                        logger.info(f"ID {texture_id}: 下载成功 - {filename} ({file_size} bytes)")
                    return True
                else:
                    os.remove(filepath)
                    logger.warning(f"ID {texture_id}: 下载的文件为空")
                    
            elif response.status_code == 404:
                logger.warning(f"ID {texture_id}: 图片不存在 (Hash: {texture_hash})")
                return False
            else:
                logger.warning(f"ID {texture_id}: 下载失败 HTTP {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            logger.warning(f"ID {texture_id} 下载失败 (尝试 {attempt + 1}/{RETRY_COUNT}): {e}")
            
        if attempt < RETRY_COUNT - 1:
            time.sleep(1)
    
    return False

def process_texture(texture_id):
    """
    处理单个皮肤ID
    
    Args:
        texture_id (int): 皮肤ID
        
    Returns:
        dict: 处理结果
    """
    result = {
        'id': texture_id,
        'success': False,
        'info_fetched': False,
        'image_downloaded': False,
        'error': None
    }
    
    try:
        texture_info = get_texture_info(texture_id)
        
        if texture_info is None:
            result['error'] = '获取皮肤信息失败'
            return result
        
        result['info_fetched'] = True
        result['texture_info'] = texture_info
        
        texture_hash = texture_info.get('hash')
        texture_name = texture_info.get('name', '')
        texture_type = texture_info.get('type', 'unknown')
        
        if not texture_hash:
            result['error'] = '皮肤信息中缺少hash'
            return result
        
        if download_texture_image(texture_hash, texture_name, texture_type, texture_id):
            result['image_downloaded'] = True
            result['success'] = True
        else:
            result['error'] = '图片下载失败'
        
        time.sleep(REQUEST_DELAY)
        
    except Exception as e:
        result['error'] = f'处理异常: {str(e)}'
        logger.error(f"ID {texture_id} 处理异常: {e}")
    
    return result

def main():
    """主函数"""
    global logger
    logger = setup_logging()
    
    print("LittleSkin皮肤爬虫脚本")
    print("=" * 50)
    
    create_dirs()
    
    try:
        start_id = int(input("请输入起始ID: "))
        end_id = int(input("请输入结束ID: "))
        
        if start_id > end_id:
            print("起始ID不能大于结束ID")
            return
        
        total_count = end_id - start_id + 1
        print(f"将处理 {total_count} 个ID (从 {start_id} 到 {end_id})")
        
        confirm = input("确认开始爬取？(y/N): ").lower()
        if confirm not in ['y', 'yes']:
            print("操作已取消")
            return
            
    except ValueError:
        print("输入的ID必须是数字")
        return
    except KeyboardInterrupt:
        print("\n操作已取消")
        return
    
    success_count = 0
    failed_count = 0
    processed_count = 0
    
    print(f"\n开始处理，使用 {MAX_WORKERS} 个并发线程...")
    print("-" * 50)
    
    try:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_id = {
                executor.submit(process_texture, texture_id): texture_id 
                for texture_id in range(start_id, end_id + 1)
            }
            
            for future in as_completed(future_to_id):
                texture_id = future_to_id[future]
                processed_count += 1
                
                try:
                    result = future.result()
                    
                    if result['success']:
                        success_count += 1
                    else:
                        failed_count += 1
                        if result.get('error'):
                            logger.debug(f"ID {texture_id}: {result['error']}")
                    
                    progress = (processed_count / total_count) * 100
                    with print_lock:
                        print(f"进度: {processed_count}/{total_count} ({progress:.1f}%) - "
                              f"成功: {success_count}, 失败: {failed_count}", end='\r')
                        
                except Exception as e:
                    failed_count += 1
                    logger.error(f"ID {texture_id} 处理异常: {e}")
    
    except KeyboardInterrupt:
        print(f"\n\n爬取被用户中断")
        print(f"已处理: {processed_count}/{total_count}")
    
    print(f"\n\n爬取完成!")
    print("=" * 50)
    print(f"总计处理: {processed_count}")
    print(f"成功下载: {success_count}")
    print(f"失败数量: {failed_count}")
    print(f"成功率: {(success_count/max(processed_count,1)*100):.1f}%")
    print(f"文件保存在: {os.path.abspath(IMGS_FOLDER)}")
    
    logger.info("爬取任务完成")

if __name__ == "__main__":
    main()