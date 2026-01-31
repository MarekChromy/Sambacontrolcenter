#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔒 Samba Control Center
Modern SMB/CIFS Management Interface
Author: Claude | Version: 2.0 | Date: 2026-01-31
"""

import os
import sys
import subprocess
import shutil
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from flask import Flask, request, render_template_string, jsonify, flash, redirect, url_for

try:
    import configparser
except ImportError:
    print("❌ ERROR: configparser module not available")
    sys.exit(1)

# =============================================================================
# Configuration & Constants
# =============================================================================

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'samba-control-2026-secret-key-change-me')
app.config['DEBUG'] = True  # Enable debug for troubleshooting

SMB_CONF = "/etc/samba/smb.conf"
BACKUP_DIR = "/etc/samba/backups"
FSTAB = "/etc/fstab"
CREDENTIALS_DIR = "/etc/samba/credentials"

# Ensure directories exist - with proper error handling
def ensure_directories():
    """Create necessary directories if they don't exist"""
    for directory in [BACKUP_DIR, CREDENTIALS_DIR]:
        try:
            if os.path.exists(directory):
                if not os.path.isdir(directory):
                    print(f"⚠️  Warning: {directory} exists but is not a directory")
                    # Try to use alternative
                    if directory == CREDENTIALS_DIR:
                        globals()['CREDENTIALS_DIR'] = "/tmp/samba_credentials"
                        os.makedirs(CREDENTIALS_DIR, mode=0o700, exist_ok=True)
            else:
                os.makedirs(directory, mode=0o700 if directory == CREDENTIALS_DIR else 0o755, exist_ok=True)
        except PermissionError:
            print(f"⚠️  Warning: No permission to create {directory}")
            if directory == CREDENTIALS_DIR:
                globals()['CREDENTIALS_DIR'] = "/tmp/samba_credentials"
                try:
                    os.makedirs(CREDENTIALS_DIR, mode=0o700, exist_ok=True)
                except:
                    pass
        except Exception as e:
            print(f"⚠️  Warning: Could not create {directory}: {e}")

ensure_directories()

# =============================================================================
# Data Models
# =============================================================================

@dataclass
class SambaShare:
    name: str
    path: str
    comment: str = ""
    writable: bool = True
    browseable: bool = True
    guest_ok: bool = False
    valid_users: str = ""
    create_mask: str = "0664"
    directory_mask: str = "0775"
    
    def to_dict(self):
        return asdict(self)

@dataclass
class CifsMount:
    remote: str
    mountpoint: str
    fstype: str
    options: str
    credentials_file: Optional[str] = None
    is_mounted: bool = False
    
    def to_dict(self):
        return asdict(self)

@dataclass
class SambaUser:
    username: str
    is_enabled: bool = True
    unix_user_exists: bool = False

# =============================================================================
# HTML Template - Modern, Professional Design
# =============================================================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="cs">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Samba Control Center</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" rel="stylesheet">
    <style>
        :root {
            --primary: #0A4D3C;
            --primary-light: #0F6B54;
            --primary-dark: #073529;
            --accent: #F59E0B;
            --accent-light: #FCD34D;
            --bg-dark: #0F172A;
            --bg-medium: #1E293B;
            --bg-light: #334155;
            --text-primary: #F8FAFC;
            --text-secondary: #CBD5E1;
            --text-muted: #94A3B8;
            --border: #475569;
            --success: #10B981;
            --warning: #F59E0B;
            --danger: #EF4444;
            --info: #3B82F6;
            --card-bg: rgba(30, 41, 59, 0.6);
            --glass-bg: rgba(15, 23, 42, 0.7);
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'IBM Plex Sans', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #0F172A 0%, #1E293B 50%, #0A4D3C 100%);
            background-attachment: fixed;
            color: var(--text-primary);
            min-height: 100vh;
            line-height: 1.6;
        }
        
        .grain {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            opacity: 0.03;
            z-index: 1;
            background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 400 400' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E");
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
            position: relative;
            z-index: 2;
        }
        
        .header {
            background: var(--glass-bg);
            backdrop-filter: blur(20px);
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 2.5rem;
            margin-bottom: 2rem;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4);
            position: relative;
            overflow: hidden;
        }
        
        .header::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, var(--primary), var(--accent), var(--primary));
            background-size: 200% 100%;
            animation: shimmer 3s linear infinite;
        }
        
        @keyframes shimmer {
            0% { background-position: -200% 0; }
            100% { background-position: 200% 0; }
        }
        
        .header h1 {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            background: linear-gradient(135deg, var(--text-primary), var(--accent-light));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .header .subtitle {
            color: var(--text-secondary);
            font-size: 1rem;
            display: flex;
            align-items: center;
            gap: 1rem;
            flex-wrap: wrap;
        }
        
        .badge {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.4rem 0.9rem;
            border-radius: 8px;
            font-size: 0.85rem;
            font-weight: 600;
            font-family: 'JetBrains Mono', monospace;
        }
        
        .badge.success {
            background: rgba(16, 185, 129, 0.15);
            color: var(--success);
            border: 1px solid rgba(16, 185, 129, 0.3);
        }
        
        .badge.warning {
            background: rgba(245, 158, 11, 0.15);
            color: var(--warning);
            border: 1px solid rgba(245, 158, 11, 0.3);
        }
        
        .badge.info {
            background: rgba(59, 130, 246, 0.15);
            color: var(--info);
            border: 1px solid rgba(59, 130, 246, 0.3);
        }
        
        .alert {
            padding: 1rem 1.25rem;
            border-radius: 12px;
            margin-bottom: 1.5rem;
            display: flex;
            align-items: center;
            gap: 1rem;
            animation: slideIn 0.3s ease-out;
            border: 1px solid;
        }
        
        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateY(-10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .alert-success {
            background: rgba(16, 185, 129, 0.15);
            border-color: rgba(16, 185, 129, 0.3);
            color: var(--success);
        }
        
        .alert-danger {
            background: rgba(239, 68, 68, 0.15);
            border-color: rgba(239, 68, 68, 0.3);
            color: var(--danger);
        }
        
        .alert-info {
            background: rgba(59, 130, 246, 0.15);
            border-color: rgba(59, 130, 246, 0.3);
            color: var(--info);
        }
        
        .alert i {
            font-size: 1.2rem;
        }
        
        .card {
            background: var(--card-bg);
            backdrop-filter: blur(10px);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 1.75rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 15px 50px rgba(0, 0, 0, 0.4);
        }
        
        .card-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 1.5rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--border);
        }
        
        .card-title {
            font-size: 1.25rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 0.75rem;
            color: var(--text-primary);
        }
        
        .card-title i {
            color: var(--accent);
            font-size: 1.4rem;
        }
        
        .grid {
            display: grid;
            gap: 1.5rem;
        }
        
        .grid-2 {
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
        }
        
        .grid-3 {
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
        }
        
        @media (max-width: 768px) {
            .grid-2, .grid-3 {
                grid-template-columns: 1fr;
            }
        }
        
        .form-group {
            margin-bottom: 1.25rem;
        }
        
        .form-label {
            display: block;
            margin-bottom: 0.5rem;
            font-weight: 500;
            color: var(--text-secondary);
            font-size: 0.9rem;
        }
        
        .form-control, .form-select {
            width: 100%;
            padding: 0.75rem 1rem;
            background: var(--bg-medium);
            border: 1px solid var(--border);
            border-radius: 10px;
            color: var(--text-primary);
            font-size: 0.95rem;
            font-family: 'IBM Plex Sans', sans-serif;
            transition: all 0.2s;
        }
        
        .form-control:focus, .form-select:focus {
            outline: none;
            border-color: var(--primary-light);
            box-shadow: 0 0 0 3px rgba(15, 107, 84, 0.2);
        }
        
        .form-control::placeholder {
            color: var(--text-muted);
        }
        
        .btn {
            padding: 0.75rem 1.5rem;
            border: none;
            border-radius: 10px;
            font-weight: 600;
            font-size: 0.95rem;
            cursor: pointer;
            transition: all 0.2s;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            text-decoration: none;
            font-family: 'IBM Plex Sans', sans-serif;
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
        }
        
        .btn:active {
            transform: translateY(0);
        }
        
        .btn-primary {
            background: linear-gradient(135deg, var(--primary), var(--primary-light));
            color: white;
        }
        
        .btn-success {
            background: linear-gradient(135deg, #059669, var(--success));
            color: white;
        }
        
        .btn-danger {
            background: linear-gradient(135deg, #DC2626, var(--danger));
            color: white;
        }
        
        .btn-warning {
            background: linear-gradient(135deg, #D97706, var(--warning));
            color: white;
        }
        
        .btn-secondary {
            background: var(--bg-light);
            color: var(--text-primary);
            border: 1px solid var(--border);
        }
        
        .btn-sm {
            padding: 0.5rem 1rem;
            font-size: 0.85rem;
        }
        
        .btn-lg {
            padding: 1rem 2rem;
            font-size: 1.05rem;
        }
        
        .table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9rem;
        }
        
        .table thead {
            background: var(--bg-light);
        }
        
        .table th {
            padding: 0.9rem 1rem;
            text-align: left;
            font-weight: 600;
            color: var(--text-secondary);
            border-bottom: 2px solid var(--border);
        }
        
        .table td {
            padding: 0.9rem 1rem;
            border-bottom: 1px solid var(--border);
        }
        
        .table tbody tr {
            transition: background 0.2s;
        }
        
        .table tbody tr:hover {
            background: rgba(255, 255, 255, 0.03);
        }
        
        .status-indicator {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.35rem 0.75rem;
            border-radius: 6px;
            font-size: 0.8rem;
            font-weight: 600;
        }
        
        .status-mounted {
            background: rgba(16, 185, 129, 0.15);
            color: var(--success);
        }
        
        .status-unmounted {
            background: rgba(148, 163, 184, 0.15);
            color: var(--text-muted);
        }
        
        code {
            background: var(--bg-dark);
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85rem;
            color: var(--accent-light);
        }
        
        pre {
            background: var(--bg-dark);
            padding: 1.25rem;
            border-radius: 10px;
            overflow-x: auto;
            border: 1px solid var(--border);
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85rem;
            line-height: 1.6;
            max-height: 400px;
            overflow-y: auto;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }
        
        .stat-card {
            background: var(--glass-bg);
            backdrop-filter: blur(10px);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.5rem;
            text-align: center;
        }
        
        .stat-value {
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, var(--text-primary), var(--accent-light));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .stat-label {
            color: var(--text-secondary);
            font-size: 0.9rem;
            margin-top: 0.5rem;
        }
        
        .action-bar {
            display: flex;
            gap: 1rem;
            flex-wrap: wrap;
            margin-top: 1.5rem;
            padding-top: 1.5rem;
            border-top: 1px solid var(--border);
        }
        
        .empty-state {
            text-align: center;
            padding: 3rem 1rem;
            color: var(--text-muted);
        }
        
        .empty-state i {
            font-size: 3rem;
            margin-bottom: 1rem;
            opacity: 0.5;
        }
        
        .footer {
            text-align: center;
            margin-top: 3rem;
            padding: 2rem;
            color: var(--text-muted);
            font-size: 0.85rem;
        }
        
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.7);
            backdrop-filter: blur(5px);
            z-index: 1000;
            align-items: center;
            justify-content: center;
        }
        
        .modal.active {
            display: flex;
        }
        
        .modal-content {
            background: var(--bg-medium);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 2rem;
            max-width: 600px;
            width: 90%;
            max-height: 90vh;
            overflow-y: auto;
        }
        
        .close-modal {
            float: right;
            font-size: 1.5rem;
            cursor: pointer;
            color: var(--text-muted);
        }
        
        .close-modal:hover {
            color: var(--text-primary);
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .loading {
            animation: pulse 2s ease-in-out infinite;
        }
    </style>
</head>
<body>
    <div class="grain"></div>
    <div class="container">
        
        <!-- Header -->
        <div class="header">
            <h1><i class="fas fa-server"></i> Samba Control Center</h1>
            <div class="subtitle">
                <span>Advanced SMB/CIFS Management</span>
                <span class="badge {% if system_info.smbd_running %}success{% else %}warning{% endif %}">
                    <i class="fas fa-circle"></i>
                    {% if system_info.smbd_running %}SMBD Active{% else %}SMBD Stopped{% endif %}
                </span>
                <span class="badge info">
                    <i class="fas fa-microchip"></i>
                    {{ system_info.hostname }}
                </span>
            </div>
        </div>

        <!-- Flash Messages -->
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }}">
                        <i class="fas fa-{% if category == 'success' %}check-circle{% elif category == 'danger' %}exclamation-circle{% else %}info-circle{% endif %}"></i>
                        <span>{{ message }}</span>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <!-- Statistics -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{{ stats.shares }}</div>
                <div class="stat-label">Samba Shares</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ stats.users }}</div>
                <div class="stat-label">Samba Users</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ stats.fstab_mounts }}</div>
                <div class="stat-label">FSTAB Entries</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ stats.active_mounts }}</div>
                <div class="stat-label">Active Mounts</div>
            </div>
        </div>

        <!-- Main Content Grid -->
        <div class="grid grid-2">
            
            <!-- Samba Shares -->
            <div class="card">
                <div class="card-header">
                    <div class="card-title">
                        <i class="fas fa-folder-open"></i>
                        Samba Shares
                    </div>
                    <button class="btn btn-primary btn-sm" onclick="showModal('addShareModal')">
                        <i class="fas fa-plus"></i> Add Share
                    </button>
                </div>
                {% if shares %}
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Share Name</th>
                                <th>Path</th>
                                <th>Access</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for share in shares %}
                                <tr>
                                    <td><strong>{{ share.name }}</strong></td>
                                    <td><code>{{ share.path }}</code></td>
                                    <td>
                                        {% if share.writable %}
                                            <span class="badge success">RW</span>
                                        {% else %}
                                            <span class="badge info">RO</span>
                                        {% endif %}
                                    </td>
                                    <td>
                                        <form method="post" style="display:inline;">
                                            <input type="hidden" name="action" value="delete_share">
                                            <input type="hidden" name="share_name" value="{{ share.name }}">
                                            <button type="submit" class="btn btn-danger btn-sm" onclick="return confirm('Delete share [{{ share.name }}]?')">
                                                <i class="fas fa-trash"></i>
                                            </button>
                                        </form>
                                    </td>
                                </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                {% else %}
                    <div class="empty-state">
                        <i class="fas fa-folder-open"></i>
                        <p>No shares configured</p>
                    </div>
                {% endif %}
            </div>

            <!-- Samba Users -->
            <div class="card">
                <div class="card-header">
                    <div class="card-title">
                        <i class="fas fa-users"></i>
                        Samba Users
                    </div>
                    <button class="btn btn-primary btn-sm" onclick="showModal('addUserModal')">
                        <i class="fas fa-user-plus"></i> Add User
                    </button>
                </div>
                {% if users %}
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Username</th>
                                <th>Status</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for user in users %}
                                <tr>
                                    <td><strong>{{ user.username }}</strong></td>
                                    <td>
                                        {% if user.is_enabled %}
                                            <span class="badge success">Enabled</span>
                                        {% else %}
                                            <span class="badge warning">Disabled</span>
                                        {% endif %}
                                    </td>
                                    <td>
                                        <form method="post" style="display:inline;">
                                            <input type="hidden" name="action" value="delete_user">
                                            <input type="hidden" name="username" value="{{ user.username }}">
                                            <button type="submit" class="btn btn-danger btn-sm" onclick="return confirm('Delete user {{ user.username }}?')">
                                                <i class="fas fa-trash"></i>
                                            </button>
                                        </form>
                                    </td>
                                </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                {% else %}
                    <div class="empty-state">
                        <i class="fas fa-users"></i>
                        <p>No Samba users configured</p>
                    </div>
                {% endif %}
            </div>
        </div>

        <!-- CIFS Mounts -->
        <div class="card">
            <div class="card-header">
                <div class="card-title">
                    <i class="fas fa-plug"></i>
                    SMB/CIFS Mount Management
                </div>
                <button class="btn btn-primary btn-sm" onclick="showModal('addMountModal')">
                    <i class="fas fa-plus"></i> Add Mount
                </button>
            </div>
            
            {% if mounts %}
                <table class="table">
                    <thead>
                        <tr>
                            <th>Remote Path</th>
                            <th>Mount Point</th>
                            <th>Type</th>
                            <th>Status</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for mount in mounts %}
                            <tr>
                                <td><code>{{ mount.remote }}</code></td>
                                <td><code>{{ mount.mountpoint }}</code></td>
                                <td><span class="badge info">{{ mount.fstype }}</span></td>
                                <td>
                                    {% if mount.is_mounted %}
                                        <span class="status-indicator status-mounted">
                                            <i class="fas fa-check-circle"></i> Mounted
                                        </span>
                                    {% else %}
                                        <span class="status-indicator status-unmounted">
                                            <i class="fas fa-circle"></i> Not Mounted
                                        </span>
                                    {% endif %}
                                </td>
                                <td>
                                    {% if mount.is_mounted %}
                                        <form method="post" style="display:inline;">
                                            <input type="hidden" name="action" value="umount">
                                            <input type="hidden" name="mountpoint" value="{{ mount.mountpoint }}">
                                            <button type="submit" class="btn btn-warning btn-sm">
                                                <i class="fas fa-eject"></i> Unmount
                                            </button>
                                        </form>
                                    {% else %}
                                        <form method="post" style="display:inline;">
                                            <input type="hidden" name="action" value="mount">
                                            <input type="hidden" name="mountpoint" value="{{ mount.mountpoint }}">
                                            <button type="submit" class="btn btn-success btn-sm">
                                                <i class="fas fa-plug"></i> Mount
                                            </button>
                                        </form>
                                    {% endif %}
                                    <form method="post" style="display:inline;">
                                        <input type="hidden" name="action" value="delete_mount">
                                        <input type="hidden" name="mountpoint" value="{{ mount.mountpoint }}">
                                        <button type="submit" class="btn btn-danger btn-sm" onclick="return confirm('Remove mount {{ mount.mountpoint }} from fstab?')">
                                            <i class="fas fa-trash"></i>
                                        </button>
                                    </form>
                                </td>
                            </tr>
                        {% endfor %}
                    </tbody>
                </table>
            {% else %}
                <div class="empty-state">
                    <i class="fas fa-plug"></i>
                    <p>No CIFS/SMB mounts configured</p>
                </div>
            {% endif %}
        </div>

        <!-- SMB Protocol Quick Selector -->
        <div class="card" style="background: linear-gradient(135deg, rgba(245, 158, 11, 0.1), rgba(15, 107, 84, 0.1)); border: 2px solid var(--accent);">
            <div class="card-header">
                <div class="card-title" style="font-size: 1.3rem;">
                    <i class="fas fa-network-wired"></i>
                    SMB Protocol Version Selector
                </div>
            </div>
            <div style="padding: 1.5rem;">
                <p style="color: var(--text-secondary); margin-bottom: 1.5rem;">
                    Choose your preferred SMB protocol version for new mounts. This setting will be remembered for the next mount you add.
                </p>
                
                <div class="grid grid-3">
                    <!-- SMB 1.0 -->
                    <div class="card" style="background: var(--bg-dark); border: 2px solid var(--border); cursor: pointer; transition: all 0.3s;" onclick="selectSMBVersion('smb1')">
                        <div style="text-align: center; padding: 1.5rem;">
                            <div style="font-size: 3rem; margin-bottom: 1rem;">🗄️</div>
                            <h3 style="color: var(--danger); margin-bottom: 0.5rem; font-size: 1.3rem;">SMB 1.0</h3>
                            <span class="badge warning" style="margin-bottom: 1rem;">Legacy / Not Secure</span>
                            <p style="color: var(--text-muted); font-size: 0.9rem; margin-top: 1rem;">
                                Old protocol for very old systems (Windows XP, old NAS). <strong>Not recommended</strong> due to security vulnerabilities.
                            </p>
                            <div style="margin-top: 1rem; padding: 0.5rem; background: rgba(239, 68, 68, 0.1); border-radius: 6px;">
                                <code style="color: var(--danger); font-size: 0.85rem;">vers=1.0</code>
                            </div>
                        </div>
                    </div>
                    
                    <!-- SMB 2.0/2.1 -->
                    <div class="card" style="background: var(--bg-dark); border: 2px solid var(--accent); cursor: pointer; transition: all 0.3s; box-shadow: 0 0 20px rgba(245, 158, 11, 0.3);" onclick="selectSMBVersion('smb2')">
                        <div style="text-align: center; padding: 1.5rem;">
                            <div style="font-size: 3rem; margin-bottom: 1rem;">📁</div>
                            <h3 style="color: var(--accent); margin-bottom: 0.5rem; font-size: 1.3rem;">SMB 2.0 / 2.1</h3>
                            <span class="badge success" style="margin-bottom: 1rem;">⭐ Recommended</span>
                            <p style="color: var(--text-muted); font-size: 0.9rem; margin-top: 1rem;">
                                Most compatible protocol. Works with Windows 7+, modern Linux/Samba servers. <strong>Best balance</strong> of compatibility and security.
                            </p>
                            <div style="margin-top: 1rem; padding: 0.5rem; background: rgba(245, 158, 11, 0.1); border-radius: 6px;">
                                <code style="color: var(--accent); font-size: 0.85rem;">vers=2.1</code>
                            </div>
                        </div>
                    </div>
                    
                    <!-- SMB 3.0+ -->
                    <div class="card" style="background: var(--bg-dark); border: 2px solid var(--border); cursor: pointer; transition: all 0.3s;" onclick="selectSMBVersion('smb3')">
                        <div style="text-align: center; padding: 1.5rem;">
                            <div style="font-size: 3rem; margin-bottom: 1rem;">🔒</div>
                            <h3 style="color: var(--success); margin-bottom: 0.5rem; font-size: 1.3rem;">SMB 3.0 / 3.1</h3>
                            <span class="badge info" style="margin-bottom: 1rem;">Modern / Encrypted</span>
                            <p style="color: var(--text-muted); font-size: 0.9rem; margin-top: 1rem;">
                                Latest protocol with encryption. For Windows 8+, modern Samba 4.0+. <strong>Most secure</strong> but may not work with older systems.
                            </p>
                            <div style="margin-top: 1rem; padding: 0.5rem; background: rgba(16, 185, 129, 0.1); border-radius: 6px;">
                                <code style="color: var(--success); font-size: 0.85rem;">vers=3.0</code>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div style="margin-top: 1.5rem; padding: 1rem; background: var(--bg-medium); border-radius: 10px; border-left: 4px solid var(--info);">
                    <div style="display: flex; align-items: center; gap: 1rem;">
                        <i class="fas fa-info-circle" style="font-size: 1.5rem; color: var(--info);"></i>
                        <div>
                            <strong style="color: var(--text-primary);">Current Selection:</strong>
                            <span id="currentSMBVersion" style="color: var(--accent); font-weight: 600; margin-left: 0.5rem;">SMB 2.1 (Auto-selected)</span>
                            <p style="color: var(--text-muted); margin-top: 0.5rem; font-size: 0.9rem;">
                                This version will be used when you click "Add Mount". You can also change it in the mount form.
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- System Actions -->
        <div class="card">
            <div class="card-header">
                <div class="card-title">
                    <i class="fas fa-tools"></i>
                    System Actions
                </div>
            </div>
            <div class="action-bar">
                <form method="post" style="display:inline;">
                    <input type="hidden" name="action" value="apply_mounts">
                    <button type="submit" class="btn btn-success btn-lg" title="Mount all entries from /etc/fstab (runs: mount -a)">
                        <i class="fas fa-bolt"></i> Apply All Mounts
                    </button>
                </form>
                <form method="post" style="display:inline;">
                    <input type="hidden" name="action" value="restart_smbd">
                    <button type="submit" class="btn btn-primary btn-lg" title="Restart Samba daemon to apply configuration changes">
                        <i class="fas fa-sync"></i> Restart Samba
                    </button>
                </form>
                <form method="post" style="display:inline;">
                    <input type="hidden" name="action" value="backup_config">
                    <button type="submit" class="btn btn-secondary btn-lg" title="Create timestamped backup of smb.conf">
                        <i class="fas fa-save"></i> Backup Config
                    </button>
                </form>
                <form method="post" style="display:inline;">
                    <input type="hidden" name="action" value="test_config">
                    <button type="submit" class="btn btn-secondary btn-lg" title="Run testparm to validate configuration">
                        <i class="fas fa-check"></i> Test Config
                    </button>
                </form>
                <button class="btn btn-secondary btn-lg" onclick="showModal('configModal')" title="View raw smb.conf file">
                    <i class="fas fa-file-code"></i> View Config
                </button>
            </div>
        </div>

        <!-- Footer -->
        <div class="footer">
            <p>Samba Control Center v2.0 | Built with Flask & Modern Design</p>
            <p>Running on {{ system_info.hostname }} | {{ system_info.current_time }}</p>
        </div>
    </div>

    <!-- Modal: Add Share -->
    <div id="addShareModal" class="modal">
        <div class="modal-content">
            <span class="close-modal" onclick="closeModal('addShareModal')">&times;</span>
            <h2 style="margin-bottom: 1.5rem;"><i class="fas fa-folder-plus"></i> Add Samba Share</h2>
            <form method="post">
                <input type="hidden" name="action" value="add_share">
                <div class="form-group">
                    <label class="form-label">Share Name</label>
                    <input type="text" name="share_name" class="form-control" required placeholder="e.g., documents">
                </div>
                <div class="form-group">
                    <label class="form-label">Directory Path</label>
                    <input type="text" name="path" class="form-control" required placeholder="/srv/samba/documents">
                </div>
                <div class="form-group">
                    <label class="form-label">Comment (Optional)</label>
                    <input type="text" name="comment" class="form-control" placeholder="Shared documents">
                </div>
                <div class="form-group">
                    <label class="form-label">Permissions</label>
                    <select name="writable" class="form-select">
                        <option value="yes">Read/Write</option>
                        <option value="no">Read-Only</option>
                    </select>
                </div>
                <div class="form-group">
                    <label class="form-label">Guest Access</label>
                    <select name="guest_ok" class="form-select">
                        <option value="no">Require Authentication</option>
                        <option value="yes">Allow Guest</option>
                    </select>
                </div>
                <div class="form-group">
                    <label class="form-label">Valid Users (Optional)</label>
                    <input type="text" name="valid_users" class="form-control" placeholder="user1, user2, @group">
                </div>
                <button type="submit" class="btn btn-primary btn-lg" style="width: 100%; margin-top: 1rem;">
                    <i class="fas fa-plus"></i> Create Share
                </button>
            </form>
        </div>
    </div>

    <!-- Modal: Add User -->
    <div id="addUserModal" class="modal">
        <div class="modal-content">
            <span class="close-modal" onclick="closeModal('addUserModal')">&times;</span>
            <h2 style="margin-bottom: 1.5rem;"><i class="fas fa-user-plus"></i> Add Samba User</h2>
            <form method="post">
                <input type="hidden" name="action" value="add_user">
                <div class="form-group">
                    <label class="form-label">Username</label>
                    <input type="text" name="username" class="form-control" required placeholder="username">
                </div>
                <div class="form-group">
                    <label class="form-label">Password</label>
                    <input type="password" name="password" class="form-control" required>
                </div>
                <div class="form-group">
                    <label class="form-label">Confirm Password</label>
                    <input type="password" name="password2" class="form-control" required>
                </div>
                <button type="submit" class="btn btn-primary btn-lg" style="width: 100%; margin-top: 1rem;">
                    <i class="fas fa-user-plus"></i> Create User
                </button>
            </form>
        </div>
    </div>

    <!-- Modal: Add Mount -->
    <div id="addMountModal" class="modal">
        <div class="modal-content">
            <span class="close-modal" onclick="closeModal('addMountModal')">&times;</span>
            <h2 style="margin-bottom: 1.5rem;"><i class="fas fa-plug"></i> Add CIFS/SMB Mount</h2>
            <form method="post">
                <input type="hidden" name="action" value="add_mount">
                <div class="form-group">
                    <label class="form-label">Remote Share (UNC Path)</label>
                    <input type="text" name="remote" class="form-control" required placeholder="//server/share">
                </div>
                <div class="form-group">
                    <label class="form-label">Local Mount Point</label>
                    <input type="text" name="mountpoint" class="form-control" required placeholder="/mnt/network">
                </div>
                
                <!-- SMB Protocol Selection - Important! -->
                <div style="margin: 1.5rem 0; padding: 1rem; background: rgba(245, 158, 11, 0.1); border-left: 4px solid var(--accent); border-radius: 8px;">
                    <div class="form-group" style="margin-bottom: 0;">
                        <label class="form-label" style="font-size: 1.1rem; font-weight: 600;">
                            🔌 Protocol / SMB Version Selection
                        </label>
                        <select name="fstype" class="form-select" style="font-size: 1rem; padding: 0.9rem;">
                            <option value="cifs">🔄 CIFS (Auto-negotiate - Best Choice)</option>
                            <option value="smb3">🔒 SMB 3.0/3.1 (Modern, Encrypted)</option>
                            <option value="smb" style="background: #FCD34D; color: #000;">📁 SMB 2.0/2.1 (Compatible) ⭐</option>
                            <option value="smbfs">🗄️ SMB 1.0 (Old, Not Secure)</option>
                        </select>
                        <small style="color: var(--accent-light); margin-top: 0.5rem; display: block; font-weight: 500;">
                            💡 TIP: CIFS automatically negotiates the best SMB version (recommended).<br>
                            📁 Select "SMB 2.0/2.1" for explicit SMB protocol.<br>
                            🔒 For modern Windows/Samba servers, use SMB3 for better security.
                        </small>
                    </div>
                </div>
                
                <div class="form-group">
                    <label class="form-label">Username</label>
                    <input type="text" name="mount_username" class="form-control" placeholder="Optional">
                </div>
                <div class="form-group">
                    <label class="form-label">Password</label>
                    <input type="password" name="mount_password" class="form-control" placeholder="Optional">
                </div>
                <div class="form-group">
                    <label class="form-label">Additional Options</label>
                    <input type="text" name="options" id="mountOptions" class="form-control" placeholder="uid=1000,gid=1000,file_mode=0755">
                    <div style="margin-top: 0.5rem; display: flex; gap: 0.5rem; flex-wrap: wrap;">
                        <button type="button" class="btn btn-secondary btn-sm" onclick="setMountOption('vers=3.0')">SMB 3.0</button>
                        <button type="button" class="btn btn-secondary btn-sm" onclick="setMountOption('vers=2.1')">SMB 2.1</button>
                        <button type="button" class="btn btn-secondary btn-sm" onclick="setMountOption('vers=1.0')">SMB 1.0</button>
                        <button type="button" class="btn btn-secondary btn-sm" onclick="setMountOption('uid=1000,gid=1000')">UID/GID</button>
                    </div>
                    <small style="color: var(--text-muted); margin-top: 0.5rem; display: block;">
                        Click buttons above to quickly add common options, or type custom options separated by commas.
                    </small>
                </div>
                <button type="submit" class="btn btn-primary btn-lg" style="width: 100%; margin-top: 1rem;">
                    <i class="fas fa-plus"></i> Add Mount
                </button>
            </form>
        </div>
    </div>

    <!-- Modal: Config View -->
    <div id="configModal" class="modal">
        <div class="modal-content" style="max-width: 900px;">
            <span class="close-modal" onclick="closeModal('configModal')">&times;</span>
            <h2 style="margin-bottom: 1.5rem;"><i class="fas fa-file-code"></i> Configuration File</h2>
            <pre>{{ config_content }}</pre>
        </div>
    </div>

    <script>
        function showModal(id) {
            document.getElementById(id).classList.add('active');
            
            // When opening Add Mount modal, pre-select the SMB version
            if (id === 'addMountModal' && window.selectedSMBVersion) {
                const smbVersionMap = {
                    'smb1': 'smbfs',
                    'smb2': 'smb',
                    'smb3': 'smb3'
                };
                const fstype = smbVersionMap[window.selectedSMBVersion] || 'cifs';
                const select = document.querySelector('#addMountModal select[name="fstype"]');
                if (select) {
                    select.value = fstype;
                }
            }
        }
        
        function closeModal(id) {
            document.getElementById(id).classList.remove('active');
        }
        
        function selectSMBVersion(version) {
            window.selectedSMBVersion = version;
            
            // Update visual selection
            const cards = document.querySelectorAll('.card[onclick^="selectSMBVersion"]');
            cards.forEach(card => {
                card.style.border = '2px solid var(--border)';
                card.style.boxShadow = 'none';
            });
            
            const selectedCard = document.querySelector(`[onclick="selectSMBVersion('${version}')"]`);
            if (selectedCard) {
                selectedCard.style.border = '2px solid var(--accent)';
                selectedCard.style.boxShadow = '0 0 20px rgba(245, 158, 11, 0.3)';
            }
            
            // Update text
            const versionNames = {
                'smb1': 'SMB 1.0 (Legacy)',
                'smb2': 'SMB 2.1 (Recommended)',
                'smb3': 'SMB 3.0 (Modern)'
            };
            
            const currentVersionSpan = document.getElementById('currentSMBVersion');
            if (currentVersionSpan) {
                currentVersionSpan.textContent = versionNames[version] || 'SMB 2.1';
            }
            
            // Show notification
            const notification = document.createElement('div');
            notification.className = 'alert alert-success';
            notification.innerHTML = `
                <i class="fas fa-check-circle"></i>
                <span>${versionNames[version]} selected! This will be used for new mounts.</span>
            `;
            notification.style.position = 'fixed';
            notification.style.top = '20px';
            notification.style.right = '20px';
            notification.style.zIndex = '10000';
            notification.style.animation = 'slideIn 0.3s ease-out';
            document.body.appendChild(notification);
            
            setTimeout(() => {
                notification.style.opacity = '0';
                notification.style.transition = 'opacity 0.5s';
                setTimeout(() => notification.remove(), 500);
            }, 2000);
        }
        
        // Set default to SMB2 on page load
        window.addEventListener('DOMContentLoaded', function() {
            selectSMBVersion('smb2');
        });
        
        function setMountOption(option) {
            const input = document.getElementById('mountOptions');
            const current = input.value.trim();
            if (current) {
                // Add to existing options
                input.value = current + ',' + option;
            } else {
                // Set as first option
                input.value = option;
            }
        }
        
        // Close modal when clicking outside
        window.onclick = function(event) {
            if (event.target.classList.contains('modal')) {
                event.target.classList.remove('active');
            }
        }
        
        // Auto-dismiss alerts after 5 seconds
        setTimeout(function() {
            const alerts = document.querySelectorAll('.alert');
            alerts.forEach(alert => {
                alert.style.transition = 'opacity 0.5s';
                alert.style.opacity = '0';
                setTimeout(() => alert.remove(), 500);
            });
        }, 5000);
    </script>
</body>
</html>
"""

# =============================================================================
# Core Functions - Configuration Management
# =============================================================================

class SambaConfig:
    """Handles Samba configuration file operations"""
    
    def __init__(self, config_path: str = SMB_CONF):
        self.config_path = config_path
        self.parser = None
        self.error = None
    
    def load(self) -> bool:
        """Load the Samba configuration file"""
        try:
            self.parser = configparser.ConfigParser(
                allow_no_value=True,
                delimiters=('=',),
                strict=False,
                interpolation=None
            )
            
            if os.path.isfile(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8', errors='replace') as f:
                    self.parser.read_file(f)
                return True
            else:
                self.error = f"Config file not found: {self.config_path}"
                return False
        except Exception as e:
            self.error = f"Failed to load config: {str(e)}"
            return False
    
    def save(self) -> bool:
        """Save the configuration back to file"""
        try:
            # Create backup first
            self.create_backup()
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                self.parser.write(f, space_around_delimiters=True)
            return True
        except Exception as e:
            self.error = f"Failed to save config: {str(e)}"
            return False
    
    def create_backup(self) -> str:
        """Create a timestamped backup of the configuration"""
        if not os.path.isfile(self.config_path):
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(BACKUP_DIR, f"smb.conf.{timestamp}.bak")
        shutil.copy2(self.config_path, backup_path)
        return backup_path
    
    def get_shares(self) -> List[SambaShare]:
        """Get all configured shares"""
        if not self.parser:
            self.load()
        
        shares = []
        for section in self.parser.sections():
            if section.lower() != 'global':
                share = SambaShare(
                    name=section,
                    path=self.parser.get(section, 'path', fallback=''),
                    comment=self.parser.get(section, 'comment', fallback=''),
                    writable=self.parser.get(section, 'writable', fallback='yes').lower() == 'yes',
                    browseable=self.parser.get(section, 'browseable', fallback='yes').lower() == 'yes',
                    guest_ok=self.parser.get(section, 'guest ok', fallback='no').lower() == 'yes',
                    valid_users=self.parser.get(section, 'valid users', fallback=''),
                    create_mask=self.parser.get(section, 'create mask', fallback='0664'),
                    directory_mask=self.parser.get(section, 'directory mask', fallback='0775')
                )
                shares.append(share)
        return shares
    
    def add_share(self, share: SambaShare) -> bool:
        """Add a new share to the configuration"""
        if not self.parser:
            self.load()
        
        try:
            if self.parser.has_section(share.name):
                self.error = f"Share '{share.name}' already exists"
                return False
            
            self.parser.add_section(share.name)
            self.parser.set(share.name, 'path', share.path)
            self.parser.set(share.name, 'writable', 'yes' if share.writable else 'no')
            self.parser.set(share.name, 'browseable', 'yes' if share.browseable else 'no')
            self.parser.set(share.name, 'guest ok', 'yes' if share.guest_ok else 'no')
            
            if share.comment:
                self.parser.set(share.name, 'comment', share.comment)
            if share.valid_users:
                self.parser.set(share.name, 'valid users', share.valid_users)
            
            self.parser.set(share.name, 'create mask', share.create_mask)
            self.parser.set(share.name, 'directory mask', share.directory_mask)
            
            return self.save()
        except Exception as e:
            self.error = f"Failed to add share: {str(e)}"
            return False
    
    def delete_share(self, share_name: str) -> bool:
        """Remove a share from the configuration"""
        if not self.parser:
            self.load()
        
        try:
            if not self.parser.has_section(share_name):
                self.error = f"Share '{share_name}' not found"
                return False
            
            self.parser.remove_section(share_name)
            return self.save()
        except Exception as e:
            self.error = f"Failed to delete share: {str(e)}"
            return False
    
    def get_config_content(self) -> str:
        """Get the raw configuration file content"""
        try:
            with open(self.config_path, 'r', encoding='utf-8', errors='replace') as f:
                return f.read()
        except Exception as e:
            return f"Error reading config: {str(e)}"

# =============================================================================
# User Management
# =============================================================================

class SambaUserManager:
    """Manages Samba users"""
    
    @staticmethod
    def get_users() -> List[SambaUser]:
        """Get list of all Samba users"""
        users = []
        try:
            result = subprocess.run(
                ['pdbedit', '-L', '-v'],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0 and result.stdout:
                current_user = None
                for line in result.stdout.split('\n'):
                    if line.startswith('Unix username:'):
                        username = line.split(':', 1)[1].strip()
                        current_user = SambaUser(username=username)
                    elif line.startswith('Account Flags:') and current_user:
                        flags = line.split(':', 1)[1].strip()
                        current_user.is_enabled = 'D' not in flags
                        users.append(current_user)
                        current_user = None
            else:
                # Fallback: Try simple list
                result2 = subprocess.run(
                    ['pdbedit', '-L'],
                    capture_output=True,
                    text=True,
                    check=False
                )
                if result2.returncode == 0 and result2.stdout:
                    for line in result2.stdout.strip().split('\n'):
                        if ':' in line:
                            username = line.split(':')[0].strip()
                            if username:
                                users.append(SambaUser(username=username, is_enabled=True))
        except FileNotFoundError:
            print("Warning: pdbedit not found - Samba may not be installed")
        except Exception as e:
            print(f"Error getting Samba users: {e}")
        
        return users
    
    @staticmethod
    def add_user(username: str, password: str) -> Tuple[bool, str]:
        """Add a new Samba user"""
        try:
            # First, create Unix user if doesn't exist
            result = subprocess.run(
                ['id', username],
                capture_output=True,
                check=False
            )
            
            if result.returncode != 0:
                # User doesn't exist, create it
                result = subprocess.run(
                    ['useradd', '-M', '-s', '/usr/sbin/nologin', username],
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                if result.returncode != 0:
                    return False, f"Failed to create Unix user: {result.stderr}"
            
            # Add to Samba
            result = subprocess.run(
                ['bash', '-c', f'echo -e "{password}\\n{password}" | smbpasswd -a -s {username}'],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0:
                return True, f"User '{username}' added successfully"
            else:
                return False, f"Failed to add Samba user: {result.stderr}"
        
        except Exception as e:
            return False, f"Error adding user: {str(e)}"
    
    @staticmethod
    def delete_user(username: str) -> Tuple[bool, str]:
        """Delete a Samba user"""
        try:
            result = subprocess.run(
                ['smbpasswd', '-x', username],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0:
                return True, f"User '{username}' deleted successfully"
            else:
                return False, f"Failed to delete user: {result.stderr}"
        
        except Exception as e:
            return False, f"Error deleting user: {str(e)}"

# =============================================================================
# Mount Management
# =============================================================================

class MountManager:
    """Manages CIFS/SMB mounts"""
    
    @staticmethod
    def get_active_mounts() -> Dict[str, bool]:
        """Get dictionary of active mount points"""
        active = {}
        try:
            with open('/proc/mounts', 'r') as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 3 and parts[2].lower() in ('cifs', 'smb', 'smb3', 'smb2', 'smbfs'):
                        active[parts[1]] = True
        except Exception as e:
            print(f"Error reading mounts: {e}")
        return active
    
    @staticmethod
    def get_fstab_mounts() -> List[CifsMount]:
        """Get CIFS/SMB mounts from /etc/fstab"""
        mounts = []
        active = MountManager.get_active_mounts()
        
        try:
            with open(FSTAB, 'r', encoding='utf-8', errors='replace') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    parts = line.split()
                    if len(parts) >= 4 and parts[2].lower() in ('cifs', 'smb', 'smb3', 'smb2', 'smbfs'):
                        # Parse credentials file from options
                        creds_file = None
                        if 'credentials=' in parts[3]:
                            for opt in parts[3].split(','):
                                if opt.startswith('credentials='):
                                    creds_file = opt.split('=', 1)[1]
                                    break
                        
                        mount = CifsMount(
                            remote=parts[0],
                            mountpoint=parts[1],
                            fstype=parts[2],
                            options=parts[3],
                            credentials_file=creds_file,
                            is_mounted=parts[1] in active
                        )
                        mounts.append(mount)
        except Exception as e:
            print(f"Error reading fstab: {e}")
        
        return mounts
    
    @staticmethod
    def add_mount(remote: str, mountpoint: str, fstype: str = 'cifs', 
                  username: str = '', password: str = '', options: str = '') -> Tuple[bool, str]:
        """Add a new mount to /etc/fstab"""
        try:
            # Create mount point if doesn't exist
            Path(mountpoint).mkdir(parents=True, exist_ok=True, mode=0o755)
            
            # Handle credentials
            creds_file = None
            if username and password:
                # Create credentials file
                creds_filename = f"creds_{mountpoint.replace('/', '_')}.txt"
                creds_file = os.path.join(CREDENTIALS_DIR, creds_filename)
                
                with open(creds_file, 'w') as f:
                    f.write(f"username={username}\n")
                    f.write(f"password={password}\n")
                
                os.chmod(creds_file, 0o600)
                
                # Add credentials option
                if options:
                    options = f"{options},credentials={creds_file}"
                else:
                    options = f"credentials={creds_file}"
            
            # Default options if none provided
            if not options:
                options = "_netdev,nofail"
            elif '_netdev' not in options:
                options = f"{options},_netdev,nofail"
            
            # Backup fstab
            shutil.copy2(FSTAB, f"{FSTAB}.bak")
            
            # Add entry to fstab
            with open(FSTAB, 'a') as f:
                f.write(f"\n# Added by Samba Control Center - {datetime.now()}\n")
                f.write(f"{remote}\t{mountpoint}\t{fstype}\t{options}\t0 0\n")
            
            return True, f"Mount added successfully"
        
        except Exception as e:
            return False, f"Error adding mount: {str(e)}"
    
    @staticmethod
    def delete_mount(mountpoint: str) -> Tuple[bool, str]:
        """Remove a mount from /etc/fstab"""
        try:
            # Backup fstab
            shutil.copy2(FSTAB, f"{FSTAB}.bak")
            
            # Read fstab and filter out the mount
            with open(FSTAB, 'r') as f:
                lines = f.readlines()
            
            # Write back without the mount
            with open(FSTAB, 'w') as f:
                skip_next_comment = False
                for line in lines:
                    if mountpoint in line and not line.strip().startswith('#'):
                        skip_next_comment = True
                        continue
                    if skip_next_comment and line.strip().startswith('# Added by Samba Control Center'):
                        skip_next_comment = False
                        continue
                    f.write(line)
            
            return True, f"Mount removed from fstab"
        
        except Exception as e:
            return False, f"Error removing mount: {str(e)}"
    
    @staticmethod
    def mount(mountpoint: str) -> Tuple[bool, str]:
        """Mount a filesystem"""
        try:
            # Ensure mount point exists
            Path(mountpoint).mkdir(parents=True, exist_ok=True, mode=0o755)
            
            result = subprocess.run(
                ['mount', mountpoint],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0:
                return True, f"Successfully mounted {mountpoint}"
            else:
                return False, f"Mount failed: {result.stderr}"
        
        except Exception as e:
            return False, f"Error mounting: {str(e)}"
    
    @staticmethod
    def umount(mountpoint: str) -> Tuple[bool, str]:
        """Unmount a filesystem"""
        try:
            result = subprocess.run(
                ['umount', mountpoint],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0:
                return True, f"Successfully unmounted {mountpoint}"
            else:
                return False, f"Unmount failed: {result.stderr}"
        
        except Exception as e:
            return False, f"Error unmounting: {str(e)}"

# =============================================================================
# System Functions
# =============================================================================

class SystemManager:
    """System-level operations"""
    
    @staticmethod
    def get_system_info() -> dict:
        """Get system information"""
        info = {
            'hostname': 'localhost',
            'current_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'smbd_running': False
        }
        
        try:
            # Get hostname
            result = subprocess.run(['hostname'], capture_output=True, text=True, check=False)
            if result.returncode == 0:
                info['hostname'] = result.stdout.strip()
            
            # Check if smbd is running
            result = subprocess.run(
                ['systemctl', 'is-active', 'smbd'],
                capture_output=True,
                text=True,
                check=False
            )
            info['smbd_running'] = result.returncode == 0
        
        except Exception as e:
            print(f"Error getting system info: {e}")
        
        return info
    
    @staticmethod
    def restart_smbd() -> Tuple[bool, str]:
        """Restart the Samba service"""
        try:
            result = subprocess.run(
                ['systemctl', 'restart', 'smbd'],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0:
                return True, "Samba service restarted successfully"
            else:
                return False, f"Failed to restart: {result.stderr}"
        
        except Exception as e:
            return False, f"Error restarting service: {str(e)}"
    
    @staticmethod
    def test_config() -> Tuple[bool, str]:
        """Test Samba configuration"""
        try:
            result = subprocess.run(
                ['testparm', '-s'],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0:
                return True, "Configuration is valid"
            else:
                return False, f"Configuration errors:\n{result.stderr}"
        
        except Exception as e:
            return False, f"Error testing config: {str(e)}"

# =============================================================================
# Flask Routes
# =============================================================================

@app.route('/', methods=['GET', 'POST'])
def index():
    """Main page"""
    
    # Load configurations
    samba_config = SambaConfig()
    samba_config.load()
    
    shares = samba_config.get_shares()
    users = SambaUserManager.get_users()
    mounts = MountManager.get_fstab_mounts()
    system_info = SystemManager.get_system_info()
    
    # Debug output
    if app.config['DEBUG']:
        print(f"DEBUG: Loaded {len(shares)} shares, {len(users)} users, {len(mounts)} mounts")
    
    # Statistics
    stats = {
        'shares': len(shares),
        'users': len(users),
        'fstab_mounts': len(mounts),
        'active_mounts': sum(1 for m in mounts if m.is_mounted)
    }
    
    # Handle POST actions
    if request.method == 'POST':
        action = request.form.get('action', '')
        
        # Samba Share Actions
        if action == 'add_share':
            share = SambaShare(
                name=request.form.get('share_name', '').strip(),
                path=request.form.get('path', '').strip(),
                comment=request.form.get('comment', '').strip(),
                writable=request.form.get('writable', 'yes') == 'yes',
                guest_ok=request.form.get('guest_ok', 'no') == 'yes',
                valid_users=request.form.get('valid_users', '').strip()
            )
            
            if not share.name or not share.path:
                flash('Share name and path are required', 'danger')
            else:
                # Create directory if doesn't exist
                try:
                    Path(share.path).mkdir(parents=True, exist_ok=True, mode=0o775)
                except Exception as e:
                    flash(f'Failed to create directory: {str(e)}', 'danger')
                    return redirect(url_for('index'))
                
                if samba_config.add_share(share):
                    flash(f'Share [{share.name}] added successfully', 'success')
                else:
                    flash(samba_config.error or 'Failed to add share', 'danger')
        
        elif action == 'delete_share':
            share_name = request.form.get('share_name', '').strip()
            if samba_config.delete_share(share_name):
                flash(f'Share [{share_name}] deleted successfully', 'success')
            else:
                flash(samba_config.error or 'Failed to delete share', 'danger')
        
        # User Actions
        elif action == 'add_user':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()
            password2 = request.form.get('password2', '').strip()
            
            if not username or not password:
                flash('Username and password are required', 'danger')
            elif password != password2:
                flash('Passwords do not match', 'danger')
            else:
                success, message = SambaUserManager.add_user(username, password)
                flash(message, 'success' if success else 'danger')
        
        elif action == 'delete_user':
            username = request.form.get('username', '').strip()
            success, message = SambaUserManager.delete_user(username)
            flash(message, 'success' if success else 'danger')
        
        # Mount Actions
        elif action == 'add_mount':
            remote = request.form.get('remote', '').strip()
            mountpoint = request.form.get('mountpoint', '').strip()
            fstype = request.form.get('fstype', 'cifs').strip()
            username = request.form.get('mount_username', '').strip()
            password = request.form.get('mount_password', '').strip()
            options = request.form.get('options', '').strip()
            
            if not remote or not mountpoint:
                flash('Remote path and mount point are required', 'danger')
            else:
                success, message = MountManager.add_mount(
                    remote, mountpoint, fstype, username, password, options
                )
                flash(message, 'success' if success else 'danger')
        
        elif action == 'delete_mount':
            mountpoint = request.form.get('mountpoint', '').strip()
            success, message = MountManager.delete_mount(mountpoint)
            flash(message, 'success' if success else 'danger')
        
        elif action == 'mount':
            mountpoint = request.form.get('mountpoint', '').strip()
            success, message = MountManager.mount(mountpoint)
            flash(message, 'success' if success else 'danger')
        
        elif action == 'umount':
            mountpoint = request.form.get('mountpoint', '').strip()
            success, message = MountManager.umount(mountpoint)
            flash(message, 'success' if success else 'danger')
        
        # System Actions
        elif action == 'apply_mounts':
            try:
                result = subprocess.run(
                    ['mount', '-a'],
                    capture_output=True,
                    text=True,
                    check=False
                )
                if result.returncode == 0:
                    flash('All mounts from /etc/fstab applied successfully! (mount -a)', 'success')
                else:
                    flash(f'Some mounts failed:\n{result.stderr}', 'danger')
            except Exception as e:
                flash(f'Error applying mounts: {str(e)}', 'danger')
        
        elif action == 'restart_smbd':
            success, message = SystemManager.restart_smbd()
            flash(message, 'success' if success else 'danger')
        
        elif action == 'backup_config':
            backup_path = samba_config.create_backup()
            if backup_path:
                flash(f'Configuration backed up to {backup_path}', 'success')
            else:
                flash('Failed to create backup', 'danger')
        
        elif action == 'test_config':
            success, message = SystemManager.test_config()
            flash(message, 'success' if success else 'danger')
        
        # Reload data after action
        return redirect(url_for('index'))
    
    # Render template
    return render_template_string(
        HTML_TEMPLATE,
        shares=shares,
        users=users,
        mounts=mounts,
        system_info=system_info,
        stats=stats,
        config_content=samba_config.get_config_content()
    )

# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == '__main__':
    print("=" * 80)
    print("🔒 SAMBA CONTROL CENTER v2.0")
    print("=" * 80)
    print(f"📁 Config: {SMB_CONF}")
    print(f"💾 Backups: {BACKUP_DIR}")
    print(f"🔑 Credentials: {CREDENTIALS_DIR}")
    print("=" * 80)
    print()
    
    # Check for root privileges
    if os.geteuid() != 0:
        print("⚠️  WARNING: Not running as root!")
        print("   Some operations may fail without sudo privileges.")
        print()
    
    # Try multiple ports
    ports = [5000, 5001, 5050, 8000]
    for port in ports:
        try:
            print(f"🚀 Starting server on port {port}...")
            print(f"🌐 Access at: http://localhost:{port}")
            print("=" * 80)
            app.run(host='0.0.0.0', port=port, debug=False)
            break
        except OSError as e:
            if 'Address already in use' in str(e):
                print(f"❌ Port {port} is in use, trying next port...")
            else:
                print(f"❌ Error on port {port}: {e}")
        except KeyboardInterrupt:
            print("\n\n👋 Shutting down gracefully...")
            sys.exit(0)
        except Exception as e:
            print(f"❌ Fatal error: {e}")
            traceback.print_exc()
            sys.exit(1)
    else:
        print("❌ Could not find an available port. Exiting.")
        sys.exit(1)
