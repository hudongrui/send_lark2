#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
import os
import logging
from typing import Set, Optional
from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("main")

IP_REGEX = re.compile(r'^((\d+).(\d+).(\d+).(\d+))\s+.*')

class IPFilter:
    """IP过滤类，用于加载和检查IP黑名单"""
    
    def __init__(self, hosts_file: str = None, secret_file: str = None,mode: str = 'whitelist'):
        """初始化IP过滤器"""
        self.mode = mode
        if self.mode == 'whitelist':
            self.hosts_file = hosts_file or os.environ.get('HOSTS_FILE', './hosts/host.list')
            logger.info(f"IPFilter mode: {self.mode} | using host_file: {self.hosts_file}")
            self.allowed_users_from_blacklist = set(os.environ.get('ALLOWED_USER', 'root,ic_admin').split(','))
            self.allowed_host_regex = set(os.environ.get('ALLOWED_HOST_REGEX', 'IC_*,FPGA_*,EMU_*').split(','))
            self.whitelisted_ips: Set[str] = set()
            self.last_loaded: float = 0
            self.load_interval: int = 300  # 60秒重新加载一次hosts文件

            self.load_hosts()
        else:
            self.blacklist_file = hosts_file or os.environ.get('IP_BLACKLIST', './conf/ip_blacklist.txt')
            self.blacklisted_ips: Set[str] = set()
            self.last_loaded: float = 0
            self.load_interval: int = 300  # 60秒重新加载一次黑名单
        
            # 初始加载IP黑名单
            self.load_blacklist()

        # self.secret_file = secret_file or os.environ.get('SECRET_FILE', './conf/.secret.txt')
        # self.load_secret()

    def load_hosts(self):
        """
        Load file from hosts.list
        """
        import time
        current_time = time.time()
        
        # 检查是否需要重新加载（避免频繁读取文件）
        if current_time - self.last_loaded < self.load_interval:
            return
        self.last_loaded = current_time

        try:
            if not os.path.exists(self.hosts_file):
                with open(self.hosts_file, 'w') as f:
                    f.write('')
                logger.info(f"Created empty hosts file at {self.hosts_file}")
                self.whitelisted_ips = set()
                return
            
            # 读取hosts文件
            new_whitelist = set()
            with open(self.hosts_file, 'r') as f:
                """
                [IC_ETX]
                10.232.73.96 ssh_host=node-10-232-73-96
                ...
                [BLACK_ETX]
                10.232.51.346 ssh_host=node-10-232-51-346
                """
                current_section = ""
                for line in f.readlines():
                    line = line.strip()
                    if line.startswith('['):
                        current_section = line.strip('[]')
                        continue

                    if self.is_allowed_section(current_section):
                        if IP_REGEX.match(line):
                            ip = IP_REGEX.match(line).group(1)
                            new_whitelist.add(ip)

            
            # 更新白名单
            self.whitelisted_ips = new_whitelist
            logger.info(f"Loaded {len(self.whitelisted_ips)} whitelisted IPs from {self.hosts_file}")
        except Exception as e:
            logger.error(f"Failed to load Host lists: {str(e)}", exc_info=True)

    def is_allowed_section(self, section: str) -> bool:
        """检查当前section是否在允许的列表中"""
        return any(re.compile(regex).match(section) for regex in self.allowed_host_regex)

    def load_blacklist(self):
        """从文件加载IP黑名单"""
        import time
        current_time = time.time()
        
        # 检查是否需要重新加载（避免频繁读取文件）
        if current_time - self.last_loaded < self.load_interval:
            return
        
        self.last_loaded = current_time
        
        try:
            # 确保文件存在
            if not os.path.exists(self.blacklist_file):
                # 如果文件不存在，创建一个空文件
                with open(self.blacklist_file, 'w') as f:
                    f.write('')
                logger.info(f"Created empty IP blacklist file at {self.blacklist_file}")
                self.blacklisted_ips = set()
                return
            
            # 读取黑名单文件
            with open(self.blacklist_file, 'r') as f:
                # 解析文件内容，忽略空行和注释行
                new_blacklist = {
                    line.strip() for line in f.readlines() 
                    if line.strip() and not line.strip().startswith('#')
                }
            
            # 更新黑名单
            self.blacklisted_ips = new_blacklist
            logger.info(f"Loaded {len(self.blacklisted_ips)} blacklisted IPs from {self.blacklist_file}")
            
        except Exception as e:
            logger.error(f"Failed to load IP blacklist: {str(e)}")
    
    def load_secret(self):
        with open(self.secret_file, 'r') as f:
            self.secret = f.read().strip()

    def check_secret(self, secret: str) -> bool:
        """
        检查请求中的secret是否与配置中的secret匹配
        """
        if not secret:
            return False
        else:
            return self.secret == secret

    def is_whitelisted(self, ip: str, user: Optional[str] = None, secret: Optional[str] = None) -> bool:
        """检查IP是否在白名单中"""
        # 先尝试重新加载白名单
        self.load_hosts()
        
        # 如果IP在白名单中，或者用户在允许的用户列表中，返回True
        is_safe_request = (ip in self.whitelisted_ips) or (user in self.allowed_users_from_blacklist)
        
        if secret:
            is_safe_request = is_safe_request or self.check_secret(secret)

        return is_safe_request

    def is_blacklisted(self, ip: str) -> bool:
        """检查IP是否在黑名单中"""
        # 先尝试重新加载黑名单
        self.load_blacklist()
        
        # 检查IP是否在黑名单中
        return ip in self.blacklisted_ips

async def ip_ban_middleware(request: Request, call_next):
    """IP拦截中间件"""
    # 获取客户端IP
    client_ip = request.client.host
    
    # 获取或创建IP过滤器实例
    if not hasattr(request.app.state, 'ip_filter'):
        request.app.state.ip_filter = IPFilter()
    
    # 检查IP是否被禁用
    if request.app.state.ip_filter.is_blacklisted(client_ip):
        logger.warning(f"Blocked request from blacklisted IP: {client_ip} to {request.url.path}")
        return JSONResponse(
            status_code=403,
            content={"error": "Forbidden: Your IP address is blocked, because your current network environment is NOT allowed to access this service."}
        )
    
    # 继续处理请求
    response = await call_next(request)
    return response


async def whitelist_middleware(request: Request, call_next):
    """IP白名单中间件"""
    # 获取客户端IP
    client_ip = request.client.host
    
    # 获取或创建IP过滤器实例
    if not hasattr(request.app.state, 'ip_filter'):
        request.app.state.ip_filter = IPFilter(mode='whitelist')
    
    # 检查IP是否在白名单中
    if not request.app.state.ip_filter.is_whitelisted(client_ip, user=request.headers.get('x-username'), secret=request.headers.get('x-secret')):
        logger.warning(f"Blocked request from non-whitelisted IP: {client_ip} to {request.url.path} | request_user: {request.headers.get('x-username')}")
        return JSONResponse(
            status_code=403,
            content={"error": "Forbidden: Your IP address is not whitelisted, please contact the administrator."}
        )
    
    # 继续处理请求
    response = await call_next(request)
    return response