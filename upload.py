#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量上传皮肤图片脚本
将爬取到的皮肤图片批量上传到API端点
"""

import requests
import json
import sys
import time
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# 配置
UPLOAD_API_URL = "http://your-domain.com/upload-img.php"  # 请修改为实际的API地址
IMGS_FOLDER = "imgs"  # 爬取脚本的图片文件夹
MAX_WORKERS = 3  # 并发上传线程数（建议不要太高）
RETRY_COUNT = 3  # 重试次数
REQUEST_DELAY = 1.0  # 请求间隔（秒）
BATCH_SIZE = 5  # 每批上传的文件数量

print_lock = Lock()

def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,  
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('upload.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

def scan_image_files():
    """
    扫描图片文件夹，获取所有PNG文件
    
    Returns:
        list: 图片文件路径列表
    """
    image_files = []
    imgs_path = Path(IMGS_FOLDER)
    
    if not imgs_path.exists():
        logger.error(f"图片文件夹不存在: {IMGS_FOLDER}")
        return []
    
    
    for subfolder in ['skins', 'capes', 'others']:
        subfolder_path = imgs_path / subfolder
        if subfolder_path.exists():
            
            png_files = list(subfolder_path.glob('*.png'))
            image_files.extend(png_files)
            logger.info(f"在 {subfolder} 文件夹中找到 {len(png_files)} 个PNG文件")
    
    logger.info(f"总计找到 {len(image_files)} 个图片文件")
    return image_files

def parse_filename_for_upload(filepath):
    """
    解析文件名并重命名为符合上传API要求的格式
    
    Args:
        filepath (Path): 文件路径
        
    Returns:
        tuple: (新文件名, 皮肤类型) 或 (None, None) 如果无法解析
    """
    filename = filepath.stem  
    
    
    folder_name = filepath.parent.name
    
    
    if '_steve' in filename.lower():
        skin_name = filename.lower().replace('_steve', '')
        skin_type = 'steve'
    elif '_alex' in filename.lower():
        skin_name = filename.lower().replace('_alex', '')
        skin_type = 'alex'
    else:
        
        if folder_name == 'capes':
            
            logger.warning(f"跳过披风文件: {filename}")
            return None, None
        else:
            
            skin_name = filename
            skin_type = 'steve'
    
    
    skin_name = "".join(c for c in skin_name if c.isalnum() or c in "_-")
    if not skin_name:
        skin_name = f"skin_{int(time.time())}"
    
    new_filename = f"{skin_name}_{skin_type}.png"
    return new_filename, skin_type

def upload_single_file(filepath):
    """
    上传单个文件
    
    Args:
        filepath (Path): 文件路径
        
    Returns:
        dict: 上传结果
    """
    result = {
        'original_file': str(filepath),
        'success': False,
        'error': None,
        'response': None
    }
    
    try:
        
        new_filename, skin_type = parse_filename_for_upload(filepath)
        
        if not new_filename:
            result['error'] = '无法解析文件名或不支持的文件类型'
            return result
        
        
        if not filepath.exists():
            result['error'] = '文件不存在'
            return result
        
        if filepath.suffix.lower() != '.png':
            result['error'] = '不是PNG文件'
            return result
        
        
        file_size = filepath.stat().st_size
        if file_size > 5 * 1024 * 1024:
            result['error'] = '文件大小超过5MB限制'
            return result
        
        if file_size == 0:
            result['error'] = '文件为空'
            return result
        
        
        for attempt in range(RETRY_COUNT):
            try:
                with open(filepath, 'rb') as f:
                    
                    files = {
                        'images': (new_filename, f, 'image/png')
                    }
                    
                    headers = {
                        'User-Agent': 'Python Batch Uploader 1.0'
                    }
                    
                    
                    logger.debug(f"尝试上传: {filepath.name} -> {new_filename}")
                    
                    response = requests.post(
                        UPLOAD_API_URL,
                        files=files,
                        headers=headers,
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        try:
                            response_data = response.json()
                            result['response'] = response_data
                            
                            if response_data.get('success'):
                                result['success'] = True
                                with print_lock:
                                    logger.info(f"上传成功: {filepath.name} -> {new_filename}")
                            else:
                                result['error'] = response_data.get('message', '上传失败')
                                
                                if 'data' in response_data and 'results' in response_data['data']:
                                    for file_result in response_data['data']['results']:
                                        if not file_result.get('success') and file_result.get('error'):
                                            logger.warning(f"文件 {file_result.get('filename')} 失败: {file_result.get('error')}")
                                
                        except json.JSONDecodeError:
                            result['error'] = f'服务器响应格式错误: {response.text[:200]}'
                            logger.error(f"JSON解析失败，响应内容: {response.text}")
                    else:
                        result['error'] = f'HTTP错误: {response.status_code}'
                        logger.error(f"HTTP错误 {response.status_code}: {response.text[:500]}")
                        
                    break  
                    
            except requests.exceptions.RequestException as e:
                logger.warning(f"上传 {filepath.name} 失败 (尝试 {attempt + 1}/{RETRY_COUNT}): {e}")
                if attempt < RETRY_COUNT - 1:
                    time.sleep(2 ** attempt)  
                else:
                    result['error'] = f'网络请求失败: {str(e)}'
        
        
        time.sleep(REQUEST_DELAY)
        
    except Exception as e:
        result['error'] = f'处理异常: {str(e)}'
        logger.error(f"处理 {filepath.name} 时发生异常: {e}")
    
    return result

def upload_batch_files(file_list):
    """
    批量上传多个文件（单个请求）
    
    Args:
        file_list (list): 文件路径列表
        
    Returns:
        dict: 批量上传结果
    """
    result = {
        'files': [str(f) for f in file_list],
        'success': False,
        'error': None,
        'response': None
    }
    
    try:
        files_data = []
        
        
        for filepath in file_list:
            new_filename, skin_type = parse_filename_for_upload(filepath)
            
            if not new_filename:
                continue
                
            if not filepath.exists() or filepath.suffix.lower() != '.png':
                continue
                
            files_data.append((filepath, new_filename))
        
        if not files_data:
            result['error'] = '没有有效的文件可上传'
            return result
        
        
        for attempt in range(RETRY_COUNT):
            try:
                files = []
                opened_files = []
                
                
                for filepath, new_filename in files_data:
                    f = open(filepath, 'rb')
                    opened_files.append(f)
                    
                    files.append(('images[]', (new_filename, f, 'image/png')))
                
                try:
                    headers = {
                        'User-Agent': 'Python Batch Uploader 1.0'
                    }
                    
                    response = requests.post(
                        UPLOAD_API_URL,
                        files=files,
                        headers=headers,
                        timeout=60
                    )
                    
                    if response.status_code == 200:
                        try:
                            response_data = response.json()
                            result['response'] = response_data
                            result['success'] = response_data.get('success', False)
                            
                            if result['success']:
                                with print_lock:
                                    logger.info(f"批量上传成功: {len(files_data)} 个文件")
                            else:
                                result['error'] = response_data.get('message', '批量上传失败')
                                
                                if 'data' in response_data and 'results' in response_data['data']:
                                    for file_result in response_data['data']['results']:
                                        if not file_result.get('success'):
                                            logger.debug(f"文件失败: {file_result.get('filename')} - {file_result.get('error')}")
                        except json.JSONDecodeError:
                            result['error'] = f'服务器响应格式错误: {response.text[:200]}'
                    else:
                        result['error'] = f'HTTP错误: {response.status_code} - {response.text[:200]}'
                        
                finally:
                    
                    for f in opened_files:
                        f.close()
                
                break  
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"批量上传失败 (尝试 {attempt + 1}/{RETRY_COUNT}): {e}")
                if attempt < RETRY_COUNT - 1:
                    time.sleep(2 ** attempt)
                else:
                    result['error'] = f'网络请求失败: {str(e)}'
        
        time.sleep(REQUEST_DELAY)
        
    except Exception as e:
        result['error'] = f'批量上传异常: {str(e)}'
        logger.error(f"批量上传时发生异常: {e}")
    
    return result

def process_files_single(image_files):
    """单文件上传模式"""
    success_count = 0
    failed_count = 0
    processed_count = 0
    total_count = len(image_files)
    
    print(f"开始单文件上传模式，使用 {MAX_WORKERS} 个并发线程...")
    print("-" * 50)
    
    try:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            
            future_to_file = {
                executor.submit(upload_single_file, filepath): filepath 
                for filepath in image_files
            }
            
            
            for future in as_completed(future_to_file):
                filepath = future_to_file[future]
                processed_count += 1
                
                try:
                    result = future.result()
                    
                    if result['success']:
                        success_count += 1
                    else:
                        failed_count += 1
                        if result.get('error'):
                            logger.debug(f"{filepath.name}: {result['error']}")
                    
                    
                    progress = (processed_count / total_count) * 100
                    with print_lock:
                        print(f"进度: {processed_count}/{total_count} ({progress:.1f}%) - "
                              f"成功: {success_count}, 失败: {failed_count}", end='\r')
                        
                except Exception as e:
                    failed_count += 1
                    logger.error(f"{filepath.name} 处理异常: {e}")
    
    except KeyboardInterrupt:
        print(f"\n\n上传被用户中断")
        print(f"已处理: {processed_count}/{total_count}")
    
    return success_count, failed_count, processed_count

def process_files_batch(image_files):
    """批量上传模式"""
    success_count = 0
    failed_count = 0
    processed_count = 0
    total_count = len(image_files)
    
    print(f"开始批量上传模式，每批 {BATCH_SIZE} 个文件...")
    print("-" * 50)
    
    try:
        
        batches = [image_files[i:i+BATCH_SIZE] for i in range(0, len(image_files), BATCH_SIZE)]
        
        for batch_num, batch_files in enumerate(batches, 1):
            result = upload_batch_files(batch_files)
            
            if result['success']:
                batch_success = len(batch_files)
                batch_failed = 0
            else:
                batch_success = 0
                batch_failed = len(batch_files)
                logger.warning(f"批次 {batch_num} 上传失败: {result.get('error')}")
            
            success_count += batch_success
            failed_count += batch_failed
            processed_count += len(batch_files)
            
            
            progress = (processed_count / total_count) * 100
            print(f"批次 {batch_num}/{len(batches)} - 进度: {processed_count}/{total_count} "
                  f"({progress:.1f}%) - 成功: {success_count}, 失败: {failed_count}")
    
    except KeyboardInterrupt:
        print(f"\n\n上传被用户中断")
        print(f"已处理: {processed_count}/{total_count}")
    
    return success_count, failed_count, processed_count

def main():
    """主函数"""
    global logger, UPLOAD_API_URL
    logger = setup_logging()
    
    print("皮肤图片批量上传脚本")
    print("=" * 50)
    
    
    image_files = scan_image_files()
    
    if not image_files:
        print("没有找到任何图片文件")
        return
    
    print(f"找到 {len(image_files)} 个图片文件")
    
    
    print("\n请选择上传模式:")
    print("1. 单文件上传（推荐，更稳定）")
    print("2. 批量上传（更快，但可能不稳定）")
    
    try:
        mode = input("请输入选择 (1/2): ").strip()
        
        if mode not in ['1', '2']:
            print("无效选择，使用默认单文件上传模式")
            mode = '1'
        
        
        print(f"\nAPI地址: {UPLOAD_API_URL}")
        confirm_api = input("API地址是否正确？(y/N): ").lower()
        if confirm_api not in ['y', 'yes']:
            new_api = input("请输入正确的API地址: ").strip()
            if new_api:
                UPLOAD_API_URL = new_api
        
        confirm = input(f"\n确认开始上传 {len(image_files)} 个文件？(y/N): ").lower()
        if confirm not in ['y', 'yes']:
            print("操作已取消")
            return
            
    except KeyboardInterrupt:
        print("\n操作已取消")
        return
    
    
    start_time = time.time()
    
    if mode == '1':
        success_count, failed_count, processed_count = process_files_single(image_files)
    else:
        success_count, failed_count, processed_count = process_files_batch(image_files)
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    
    print(f"\n\n上传完成!")
    print("=" * 50)
    print(f"总计处理: {processed_count}")
    print(f"成功上传: {success_count}")
    print(f"失败数量: {failed_count}")
    print(f"成功率: {(success_count/max(processed_count,1)*100):.1f}%")
    print(f"耗时: {elapsed_time:.1f} 秒")
    print(f"平均速度: {(processed_count/max(elapsed_time,1)):.1f} 文件/秒")
    
    logger.info("批量上传任务完成")

if __name__ == "__main__":
    main()
