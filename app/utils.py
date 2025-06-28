import pandas as pd
import re
import os
from typing import Optional, List

def create_directories():
    """创建必要的目录（uploads和output）"""
    directories = ['uploads', 'output']
    for dir_name in directories:
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)
            print(f"已创建目录: {dir_name}")

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    allowed_extensions = {'csv', 'xlsx', 'xls'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions


def query_matching_data(
    demand_file_path: str,
    store_file_path: str,
    output_file_path: str,
    output_format: str = "csv"  # 可选 "csv" 或 "html"
) -> Optional[str]:
    """
    按demand文件原始顺序逐行查询材料匹配结果，并支持HTML高亮输出
    
    参数:
        demand_file_path: demand文件路径
        store_file_path: store文件路径
        output_file_path: 结果文件路径
        output_format: 输出格式，支持"csv"或"html"
        
    返回:
        成功返回结果路径，失败返回None
    """
    try:
        # 1. 验证文件存在性
        if not os.path.exists(demand_file_path):
            raise FileNotFoundError(f"demand文件不存在: {demand_file_path}")
        if not os.path.exists(store_file_path):
            raise FileNotFoundError(f"store文件不存在: {store_file_path}")

        # 2. 读取文件数据
        demand_df = _read_file(demand_file_path)
        store_df = _read_file(store_file_path)

        # 3. 验证列存在性
        _validate_columns(demand_df, ['材料'], "demand")
        _validate_columns(store_df, ['摘要', '供应商/客户名称', '单据金额'], "store")

        # 4. 提取材料（保留原始顺序，过滤纯斜杠或空白）
        materials = []
        invalid_count = 0
        for idx, row in demand_df.iterrows():
            material = str(row['材料']).strip()
            if re.match(r'^[\/\s]*$', material):
                invalid_count += 1
                continue
            materials.append((idx + 1, material))  # (顺序号, 材料)
        
        if not materials:
            raise ValueError(f"demand文件中未找到有效材料（过滤了{invalid_count}条无效记录）")
        
        print(f"已过滤{invalid_count}条无效材料，剩余{len(materials)}条有效材料")

        # 5. 逐材料匹配（按原始顺序）
        all_matches = []
        for order, material in materials:
            escaped_material = re.escape(material)
            matches = store_df[store_df['摘要'].str.contains(escaped_material, na=False, regex=True)].copy()
            
            if not matches.empty:
                # 添加材料顺序和原始材料列
                matches['材料顺序'] = order
                matches['原始材料'] = material
                
                # 仅当输出格式为HTML时高亮摘要
                if output_format.lower() == "html":
                    matches['摘要'] = matches['摘要'].apply(
                        lambda x: _highlight_matches(x, material)
                    )
                
                all_matches.append(matches[['材料顺序', '原始材料', '供应商/客户名称', '单据金额', '摘要']])

        # 6. 合并所有匹配结果
        if not all_matches:
            print("未找到任何匹配记录")
            return None
            
        result_df = pd.concat(all_matches, ignore_index=True)
        
        # 7. 按材料在demand中的顺序排序
        result_df = result_df.sort_values('材料顺序')

        # 8. 保存结果
        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
        
        if output_format.lower() == "html":
            # 生成HTML表格并添加高亮样式
            html_content = _generate_html(result_df)
            with open(output_file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"成功生成HTML报告，包含{len(result_df)}条匹配记录")
        else:
            # 保存为CSV
            result_df.to_csv(output_file_path, index=False, encoding='utf-8-sig')
            print(f"成功保存{len(result_df)}条匹配记录到CSV")
            
        return output_file_path

    except FileNotFoundError as e:
        print(f"文件错误: {str(e)}")
        return None
    except ValueError as e:
        print(f"数据错误: {str(e)}")
        return None
    except Exception as e:
        print(f"处理异常: {str(e)}")
        return None


def _read_file(file_path: str) -> pd.DataFrame:
    """根据文件扩展名读取文件（支持csv/xlsx/xls）"""
    if file_path.endswith('.csv'):
        return pd.read_csv(file_path)
    elif file_path.endswith(('.xlsx', '.xls')):
        return pd.ExcelFile(file_path).parse()
    else:
        raise ValueError(f"不支持的文件格式: {os.path.splitext(file_path)[1]}")


def _validate_columns(df: pd.DataFrame, required_cols: List[str], file_type: str):
    """验证数据框是否包含必要列"""
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"{file_type}文件缺少必要列: {', '.join(missing_cols)}")


def _highlight_matches(text: str, keyword: str) -> str:
    """在文本中高亮显示匹配的关键词"""
    if not text or pd.isna(text):
        return ""
        
    # 使用正则表达式查找并高亮所有匹配项
    pattern = re.compile(re.escape(keyword), re.IGNORECASE)
    highlighted = pattern.sub(f'<span class="highlight">{keyword}</span>', str(text))
    
    return highlighted


def _generate_html(df: pd.DataFrame) -> str:
    """生成包含高亮样式的HTML表格"""
    # 基本HTML结构和CSS样式
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>材料匹配结果</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .header {{ text-align: center; margin-bottom: 20px; }}
            .stats {{ font-size: 16px; color: #666; margin-bottom: 10px; }}
            .filter {{ margin-bottom: 20px; }}
            .filter input {{ padding: 8px; border: 1px solid #ddd; border-radius: 4px; }}
            .filter button {{ padding: 8px 15px; background-color: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer; }}
            .filter button:hover {{ background-color: #45a049; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ padding: 10px; border: 1px solid #ddd; text-align: left; }}
            th {{ background-color: #f2f2f2; font-weight: bold; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
            tr:hover {{ background-color: #f5f5f5; }}
            .highlight {{ background-color: #FFFF00; font-weight: bold; }}
            .pagination {{ margin-top: 20px; text-align: center; }}
            .pagination button {{ padding: 5px 10px; margin: 0 2px; border: 1px solid #ddd; border-radius: 4px; cursor: pointer; }}
            .pagination button.active {{ background-color: #4CAF50; color: white; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>材料匹配结果</h1>
            <div class="stats">共找到 {len(df)} 条匹配记录</div>
        </div>
        
        <div class="filter">
            <input type="text" id="searchInput" placeholder="搜索材料...">
            <button onclick="searchTable()">搜索</button>
        </div>
        
        {df.to_html(escape=False, na_rep='nan', classes='result-table')}
        
        <div class="pagination" id="pagination"></div>
        
        <script>
            // 搜索功能
            function searchTable() {{
                var input, filter, table, tr, td, i, txtValue;
                input = document.getElementById("searchInput");
                filter = input.value.toUpperCase();
                table = document.querySelector(".result-table");
                tr = table.getElementsByTagName("tr");
                
                // 从1开始跳过表头
                for (i = 1; i < tr.length; i++) {{
                    td = tr[i].getElementsByTagName("td")[1];  // 第2列（材料列）
                    if (td) {{
                        txtValue = td.textContent || td.innerText;
                        if (txtValue.toUpperCase().indexOf(filter) > -1) {{
                            tr[i].style.display = "";
                        }} else {{
                            tr[i].style.display = "none";
                        }}
                    }}
                }}
            }}
            
            // 分页功能（可根据需要扩展）
            function setupPagination() {{
                // 示例分页逻辑，实际实现需要根据行数和每页显示数量计算
                var pagination = document.getElementById("pagination");
                pagination.innerHTML = '<button class="active">1</button>';
            }}
            
            // 页面加载完成后初始化
            window.onload = function() {{
                setupPagination();
            }}
        </script>
    </body>
    </html>
    """
    
    return html_template


# 示例调用
if __name__ == "__main__":
    # 输出为HTML格式
    result_path = query_matching_data(
        demand_file_path="../data/demand.xlsx",
        store_file_path="./data/store.xls",
        output_file_path="./output/query_result.html",
        output_format="html"
    )
    
    # 如需输出为CSV，修改output_format为"csv"即可
    
    if result_path:
        print(f"查询成功，结果已保存至: {result_path}")
    else:
        print("查询失败，请检查错误信息")