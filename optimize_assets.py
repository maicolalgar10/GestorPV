"""Script de optimización de assets:
- Minifica CSS y JS (sobrescribe archivos creando copia .bak)
- Optimiza imágenes JPEG/PNG (reduce calidad y activa optimize)

Uso:
    python optimize_assets.py [--dry-run]

Advertencia: El script sobrescribe archivos y crea copias de seguridad con extensión .bak
"""
from __future__ import annotations
import argparse
import os
import io
from PIL import Image
from rcssmin import cssmin
from rjsmin import jsmin

STATIC_DIR = os.path.join(os.path.dirname(__file__), 'static')


def backup_and_write(path: str, content: bytes):
    bak = path + '.bak'
    if not os.path.exists(bak):
        try:
            os.replace(path, bak)
        except Exception:
            # If replace fails (e.g., first time), just copy
            try:
                with open(path, 'rb') as fsrc, open(bak, 'wb') as fdst:
                    fdst.write(fsrc.read())
            except Exception:
                pass
    with open(path, 'wb') as f:
        f.write(content)


def minify_css_file(path: str, dry_run: bool = False):
    with open(path, 'r', encoding='utf-8') as f:
        src = f.read()
    minified = cssmin(src)
    if dry_run:
        print('[DRY] Minificar CSS:', path)
        return
    backup_and_write(path, minified.encode('utf-8'))
    print('Minificado CSS:', path)


def minify_js_file(path: str, dry_run: bool = False):
    with open(path, 'r', encoding='utf-8') as f:
        src = f.read()
    minified = jsmin(src)
    if dry_run:
        print('[DRY] Minificar JS:', path)
        return
    backup_and_write(path, minified.encode('utf-8'))
    print('Minificado JS:', path)


def optimize_image_file(path: str, dry_run: bool = False, quality: int = 75):
    try:
        img = Image.open(path)
    except Exception as e:
        print('No se pudo abrir imagen:', path, '->', e)
        return
    fmt = img.format
    if fmt not in ('JPEG', 'JPG', 'PNG'):
        print('Formato no soportado (skipping):', path)
        return
    if dry_run:
        print('[DRY] Optimizar imagen:', path)
        return
    # crear backup
    bak = path + '.bak'
    if not os.path.exists(bak):
        try:
            os.replace(path, bak)
        except Exception:
            try:
                with open(path, 'rb') as fsrc, open(bak, 'wb') as fdst:
                    fdst.write(fsrc.read())
            except Exception:
                pass
    try:
        if fmt in ('JPEG', 'JPG'):
            img = img.convert('RGB')
            img.save(path, 'JPEG', optimize=True, quality=quality)
        else:  # PNG
            img.save(path, 'PNG', optimize=True)
        print('Optimizada imagen:', path)
    except Exception as e:
        print('Error optimizando:', path, '->', e)


def walk_and_optimize(dry_run: bool = False):
    # CSS
    css_dir = os.path.join(STATIC_DIR, 'css')
    if os.path.isdir(css_dir):
        for root, _, files in os.walk(css_dir):
            for f in files:
                if f.lower().endswith('.css'):
                    minify_css_file(os.path.join(root, f), dry_run=dry_run)

    # JS
    js_dir = os.path.join(STATIC_DIR, 'js')
    if os.path.isdir(js_dir):
        for root, _, files in os.walk(js_dir):
            for f in files:
                if f.lower().endswith('.js'):
                    minify_js_file(os.path.join(root, f), dry_run=dry_run)

    # Imágenes en static/img
    img_dir = os.path.join(STATIC_DIR, 'img')
    if os.path.isdir(img_dir):
        for root, _, files in os.walk(img_dir):
            for f in files:
                if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                    optimize_image_file(os.path.join(root, f), dry_run=dry_run)

    # Imágenes en uploads
    uploads_dir = os.path.join(STATIC_DIR, 'uploads')
    if os.path.isdir(uploads_dir):
        for root, _, files in os.walk(uploads_dir):
            for f in files:
                if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                    optimize_image_file(os.path.join(root, f), dry_run=dry_run)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Optimizar assets estáticos')
    parser.add_argument('--dry-run', action='store_true', help='No sobrescribir archivos, mostrar acciones')
    parser.add_argument('--quality', type=int, default=75, help='Calidad JPEG (1-95)')
    args = parser.parse_args()
    walk_and_optimize(dry_run=args.dry_run)
