import mammoth
import os
import sys

def convert_docx_to_html(input_path, output_dir):
    with open(input_path, "rb") as docx_file:
        result = mammoth.convert_to_html(docx_file)
        html = result.value
        
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "instruction.html")
    
    with open(output_path, "w", encoding="utf-8") as html_file:
        html_file.write(html)
    
    print(f"Конвертация завершена. HTML сохранён в {output_path}")
    return output_path
