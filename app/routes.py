from flask import Blueprint, render_template, request, send_file, flash, redirect, url_for
import os
# from werkzeug.utils import secure_filename
from app.utils import query_matching_data, allowed_file, safe_filename

main_bp = Blueprint('main', __name__)

@main_bp.route('/', methods=['GET', 'POST'])
def index():
    """文件上传和查询首页"""
    if request.method == 'POST':
        # 检查是否有文件上传
        if 'demand_file' not in request.files or 'store_file' not in request.files:
            flash('未找到上传的文件', 'error')
            return redirect(request.url)
            
        demand_file = request.files['demand_file']
        store_file = request.files['store_file']
        
        # 检查文件名是否为空
        if demand_file.filename == '' or store_file.filename == '':
            flash('文件名不能为空', 'error')
            return redirect(request.url)
            
        # 检查文件格式是否允许
        if not (allowed_file(demand_file.filename) and allowed_file(store_file.filename)):
            flash('仅支持上传 csv、xlsx 或 xls 格式的文件', 'error')
            return redirect(request.url)
            
        try:
            # 保存上传的文件
            demand_path = os.path.join('uploads', safe_filename(demand_file.filename))
            store_path = os.path.join('uploads', safe_filename(store_file.filename))
            print(demand_path)
            print(store_path)
            demand_file.save(demand_path)
            store_file.save(store_path)
            
            # 执行查询
            output_path = os.path.join('output', 'query_result.csv')
            result = query_matching_data(demand_path, store_path, output_path)
            html_output_path = os.path.join(os.getcwd(), "output", "query_result.html")
            result2 = query_matching_data(
                demand_file_path=demand_path,
                store_file_path=store_path,
                output_file_path=html_output_path,
                output_format="html"
            )
            
            if result:
                return redirect(url_for('main.result', file=output_path))
            else:
                flash('未找到匹配的记录', 'info')
                return redirect(request.url)
                
        except Exception as e:
            flash(f'处理文件时出错: {str(e)}', 'error')
            return redirect(request.url)
            
    return render_template('index.html')

@main_bp.route('/result')
def result():
    """查询结果展示页面"""
    file_path = request.args.get('file')
    if not file_path or not os.path.exists(file_path):
        flash('结果文件不存在', 'error')
        return redirect(url_for('main.index'))
        
    # 读取结果文件
    try:
        import pandas as pd
        df = pd.read_csv(file_path)
        return render_template('result.html', results=df.to_dict('records'))
    except Exception as e:
        flash(f'读取结果文件时出错: {str(e)}', 'error')
        return redirect(url_for('main.index'))

from flask import send_file, current_app
import os

@main_bp.route('/download_csv')
def download_csv():
    """下载结果文件（固定路径版）"""
    # 定义完整文件路径（项目根目录的output/下）
    file_path = os.path.join(os.getcwd(), "output", "query_result.csv")
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        return "文件不存在", 404
        
    try:
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        return f"下载出错: {str(e)}", 500
    
@main_bp.route('/download_html')
def download_html():
    """下载结果文件（固定路径版）"""
    # 定义完整文件路径（项目根目录的output/下）
    file_path = os.path.join(os.getcwd(), "output", "query_result.html")
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        return "文件不存在", 404
        
    try:
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        return f"下载出错: {str(e)}", 500