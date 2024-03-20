from flask import Flask, request, send_file, render_template,url_for
import regex as re
import os

app = Flask(__name__)

# パターンとその名称を辞書で定義
patterns = {
    #"1文の長さが80文字以上": r"(?:[^\x00-\x7F]|[\x80-\xFF]){80,}",
    "カッコの全角半角不一致": r"（(?![^（]*）)|\((?![^\(]*\))",
    "カッコと単語の間に半角スペースがない": r"[\p{Han}\p{Hiragana}\p{Katakana}a-zA-Z]\(|\)[\p{Han}\p{Hiragana}\p{Katakana}a-zA-Z]",
    "ソースファイルで未改行": r'(。[^。]*。)',
    "ダブルクオーテーションの誤り": r'"',
    "pp.とページ番号の間に半角スペースがない": r"pp\.(?!\s\d+--\d+)",
    "全角アルファベット": r"[\uFF21-\uFF3A\uFF41-\uFF5A]",
    "半角カタカナ": r"[\uFF61-\uFF9F]+",
    "半角カンマ": r"[^\x00-\x7F],",
    "半角ピリオド": r"[^\x00-\x7F]\.",
    "日本語に半角カッコ": r"\([^\x00-\x7F]|[^\x00-\x7F]\)",
    "英語に全角カッコ": r"（[\x00-\x7F]|[\x00-\x7F]）",
    "体言止め": r"[\u4E00-\u9FFF]。",
    "句点の後に参考文献": r"。\\cite|\. \\cite",
    "半角文字と参考文献の間に半角スペースがない": r"[\x21-\x7e]\\cite",
    "4桁以上の数字にカンマがない": r"\d{4,}",
    "「です」「ます」調": r"です|ます|でしょう|でした|ました|ません",
}

# ファイルをアップロードし、処理するエンドポイント
@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # ファイルがリクエストに含まれているか確認
        if 'file' not in request.files:
            return 'ファイルがありません', 400
        file = request.files['file']
        if file.filename == '':
            return 'ファイルが選択されていません', 400
        if file:
            # アップロードされたファイルを一時ファイルとして保存
            input_file_path = 'input.txt'
            file.save(input_file_path)
            # 出力ファイルの名前を設定
            output_file_name = f"result_{file.filename}"
            output_file_path = os.path.join('output', output_file_name)
            results = []
            # ファイルを処理
            process_file(input_file_path, output_file_path,results)
            # 処理後のファイルのダウンロードリンクを提供するページを表示
            download_url = url_for('download_file', filename=output_file_name)
            return render_template('download.html', download_url=download_url, results=results)

    # GETリクエストの場合、ファイルアップロードフォームを表示（変更点）
    return render_template('index.html')

@app.route('/download/<filename>')
def download_file(filename):
    path = os.path.join('output', filename)
    return send_file(path, as_attachment=True)

def output_result(output_file,line,line_number,name,results):
    result = f"Line {line_number}: '{line.strip()}' matches pattern '{name}'\n"
    print(result, end='')  # コンソールに表示
    output_file.write(result)  # ファイルに保存
    output_file.write("\n")  # ファイルに保存
    results.append(result)

def find_and_save_patterns(file_path, output_file_path, patterns,results):
    """
    テキストファイルから指定された正規表現パターンにマッチする行を探し、
    そのパターンの名称とマッチした行を別のファイルに保存する。

    :param file_path: テキストファイルのパス
    :param output_file_path: 結果を保存するファイルのパス
    :param patterns: 正規表現パターンとその名称を含む辞書
    """
    bibflag = False

    with open(file_path, 'r', encoding='utf-8') as file, \
        open(output_file_path, 'w', encoding='utf-8') as output_file:
        for line_number, line in enumerate(file, start=1):
            if line.startswith('%') or line.startswith('\\') or "助成" in line:
                if line.startswith('\\bibitem'): bibflag = True
                continue
            for name, pattern in patterns.items():
                if name != "半角文字と参考文献の間に半角スペースがない" and name != "句点の後に参考文献":
                    clean_line = re.sub(r'\\cite\{[^}]*\}', '', line)
                search = re.search(pattern, clean_line)
                if search:
                    if name == "4桁以上の数字にカンマがない" and bibflag: continue
                    output_result(output_file,line,line_number,name,results)
            if bibflag and line.endswith("."): bibflag = False

def process_file(input_file_path, output_file_path,results):
    # 関数を実行
    find_and_save_patterns(input_file_path, output_file_path, patterns, results)
    pass

if __name__ == '__main__':
    app.run(debug=True)
