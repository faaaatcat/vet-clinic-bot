import os
from datetime import datetime

def create_code_listing(project_path, output_file, extensions=['.py', '.txt', '.md']):
    with open(output_file, 'w', encoding='utf-8') as outfile:
        outfile.write(f"Листинг проекта: {os.path.basename(project_path)}\n")
        outfile.write(f"Создан: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        outfile.write("="*50 + "\n\n")
        
        for root, dirs, files in os.walk(project_path):
            # Пропускаем служебные папки
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'venv']]
            
            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, project_path)
                    
                    outfile.write(f"\n{'='*60}\n")
                    outfile.write(f"ФАЙЛ: {relative_path}\n")
                    outfile.write(f"{'='*60}\n\n")
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as infile:
                            content = infile.read()
                            outfile.write(content)
                            outfile.write("\n")
                    except Exception as e:
                        outfile.write(f"Ошибка чтения файла: {e}\n")

if __name__ == "__main__":
    project_path = "."  # Текущая папка
    output_file = "project_listing.txt"
    create_code_listing(project_path, output_file)
    print(f"Листинг создан: {output_file}")
