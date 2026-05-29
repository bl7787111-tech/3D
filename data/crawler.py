"""
彩票数据爬取模块
"""

import pandas as pd
import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict, List
import logging
from config import Config


logger = logging.getLogger(__name__)


class LotteryCrawler:
    """彩票数据爬取器"""
    
    def __init__(self):
        """初始化爬取器"""
        self.config = Config()
        self.timeout = self.config.CRAWLER_TIMEOUT
        self.retry_times = self.config.CRAWLER_RETRY_TIMES
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def fetch_from_excel(self, url: str) -> Optional[pd.DataFrame]:
        """
        从Excel文件爬取数据
        
        Args:
            url: Excel文件URL
            
        Returns:
            DataFrame或None
        """
        try:
            df = pd.read_excel(url)
            logger.info(f"Successfully fetched data from {url}")
            return df
        except Exception as e:
            logger.error(f"Failed to fetch from {url}: {str(e)}")
            return None
    
    def fetch_from_html(self, url: str) -> Optional[pd.DataFrame]:
        """
        从HTML页面爬取数据
        
        Args:
            url: 网页URL
            
        Returns:
            DataFrame或None
        """
        try:
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 查找数据表格
            table = soup.find('table', class_='lottery-table')
            if table:
                df = pd.read_html(str(table))[0]
                logger.info(f"Successfully fetched data from {url}")
                return df
            
            return None
        except Exception as e:
            logger.error(f"Failed to fetch from {url}: {str(e)}")
            return None
    
    def fetch_from_api(self, api_url: str) -> Optional[pd.DataFrame]:
        """
        从API接口爬取数据
        
        Args:
            api_url: API URL
            
        Returns:
            DataFrame或None
        """
        try:
            response = requests.get(api_url, headers=self.headers, timeout=self.timeout)
            data = response.json()
            
            if 'data' in data:
                df = pd.DataFrame(data['data'])
                logger.info(f"Successfully fetched data from API: {api_url}")
                return df
            
            return None
        except Exception as e:
            logger.error(f"Failed to fetch from API {api_url}: {str(e)}")
            return None
    
    def fetch_with_retry(self, url: str) -> Optional[pd.DataFrame]:
        """
        带重试机制的数据爬取
        
        Args:
            url: 数据源URL
            
        Returns:
            DataFrame或None
        """
        for attempt in range(self.retry_times):
            try:
                if url.endswith('.xls') or url.endswith('.xlsx'):
                    result = self.fetch_from_excel(url)
                elif url.startswith('http') and '/api/' in url:
                    result = self.fetch_from_api(url)
                else:
                    result = self.fetch_from_html(url)
                
                if result is not None and not result.empty:
                    return result
                
                logger.warning(f"Attempt {attempt + 1} failed for {url}")
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} error: {str(e)}")
        
        return None
    
    def fetch_all_sources(self) -> Optional[pd.DataFrame]:
        """
        从所有数据源按优先级爬取数据
        
        Returns:
            DataFrame或None
        """
        sources = self.config.DATA_SOURCES
        
        # 尝试主数据源
        df = self.fetch_with_retry(sources['primary'])
        if df is not None and not df.empty:
            return df
        
        # 尝试备用数据源
        for key in ['backup1', 'backup2']:
            if key in sources:
                df = self.fetch_with_retry(sources[key])
                if df is not None and not df.empty:
                    return df
        
        logger.error("Failed to fetch data from all sources")
        return None
    
    def validate_data(self, df: pd.DataFrame) -> bool:
        """
        验证数据完整性
        
        Args:
            df: 数据框
            
        Returns:
            是否有效
        """
        required_columns = ['期号', '号码'] or ['百', '十', '个']
        
        if '号码' in df.columns:
            # 验证号码格式
            for code in df['号码']:
                if not isinstance(code, (int, str)) or len(str(code)) != 3:
                    logger.warning(f"Invalid code format: {code}")
                    return False
        
        return True
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        清洗数据
        
        Args:
            df: 原始数据框
            
        Returns:
            清洗后的数据框
        """
        # 删除空行
        df = df.dropna()
        
        # 提取数字位
        if '号码' in df.columns:
            df['百'] = df['号码'].astype(str).str[0].astype(int)
            df['十'] = df['号码'].astype(str).str[1].astype(int)
            df['个'] = df['号码'].astype(str).str[2].astype(int)
        
        # 删除重复记录
        df = df.drop_duplicates(subset=['期号'])
        
        # 按日期排序
        if '日期' in df.columns:
            df = df.sort_values('日期', ascending=False)
        
        logger.info(f"Data cleaning completed. Total records: {len(df)}")
        return df


# ==================== 导出接口 ====================
__all__ = ['LotteryCrawler']
