from flask import Flask, request, send_file, render_template, url_for
import regex as re
import os

app = Flask(__name__)

# パターンとその名称を辞書で定義
patterns = {
    #"1文の長さが長すぎる": r".{100,}",
    # "pp.とページ番号の間に半角スペースがない": r"pp\.(?!\s\d+--\d+)",
    "「です」「ます」調": r"です|ます|でしょう|でした|ました|ません",
    "体言止め": r"[\u4E00-\u9FFF]。",
    "半角カタカナ": r"[\uFF61-\uFF9F]+",
    "全角アルファベット": r"[\uFF21-\uFF3A\uFF41-\uFF5A]",
    "全角スペース": r"\u3000",
    "日本語にダブルクオーテーション": r"(``[\w\s]+'')|([^\x00-\x7F][''])|([``][^\x00-\x7F])",
    "英語にカギカッコ": r"[「][\x20-\x7E]+[」]",
    "日本語に半角カンマ": r"[^\x00-\x7F],",
    "日本語に半角ピリオド": r"[^\x00-\x7F]\.",
    "カッコの全角半角不一致": r"（(?![^（]*）)|\((?![^\(]*\))",
    "日本語に半角カッコ": r"\([^\x00-\x7F]|[^\x00-\x7F]\)",
    "英語に全角カッコ": r"[（][\x20-\x7E]+[）]",
    "ダブルクオーテーションの誤り": r'"',
    "カッコとカッコの外側の単語の間に半角スペースがない": r"[\p{Han}\p{Hiragana}\p{Katakana}a-zA-Z]\(|\)[\p{Han}\p{Hiragana}\p{Katakana}a-zA-Z]",
    "半角カンマと英単語の間に半角スペースがない": r",[a-zA-Z0-9!-/:-@[-`{-~]+",
    "ソースファイルで未改行": r"(。[^。]*。)",
    "句点の後に参考文献": r"。\\cite|\. \\cite",
    "半角文字と参考文献の間に半角スペースがない": r"[\x21-\x7e]\\cite",
    "4桁以上の数字にカンマがない": r"\d{4,}",
}


@app.route("/", methods=["GET", "POST"])
def upload_file():
    if request.method == "POST":
        file = request.files["file"]
        if file:
            # アップロードされたファイルを一時ファイルとして保存
            input_file_path = os.path.join("tmp", f"input_{file.filename}")
            file.save(input_file_path)
            # 出力ファイルの名前を設定
            output_file_name = f"result_{file.filename}"
            output_file_path = os.path.join("tmp", output_file_name)
            results = []
            # ファイルを処理
            process_file(input_file_path, output_file_path, results)
            # 処理後のファイルのダウンロードリンクを提供するページを表示
            download_url = url_for("download_file", filename=output_file_name)
            cleanup_url = url_for("cleanup", filename=file.filename)
            return render_template(
                "download.html",
                download_url=download_url,
                cleanup_url=cleanup_url,
                results=results,
            )

    # GETリクエストの場合、またはエラー発生時
    return render_template("index.html")

@app.route("/download/<filename>")
def download_file(filename):
    path = os.path.join("tmp", filename)
    return send_file(path, as_attachment=True)


@app.route("/cleanup/<filename>", methods=["POST"])
def cleanup(filename):
    try:
        os.remove(os.path.join("tmp", f"result_{filename}"))
        os.remove(os.path.join("tmp", f"input_{filename}"))
        return "File deleted successfully", 200
    except Exception as e:
        return str(e), 500


def output_result(output_file, line, line_number, name, results):
    result = [f"{line_number}", f"{name}", f"{line.strip()}"]
    print_result = f"{result[0]} : {result[1]} - {result[2]}\n"
    output_file.write(print_result)  # ファイルに保存
    results.append(result)


def find_and_save_patterns(file_path, output_file_path, patterns, results):
    bibflag = False
    cflag = False
    with open(file_path, "r", encoding="utf-8") as file, open(
        output_file_path, "w", encoding="utf-8"
    ) as output_file:
        output_file.write("行数, 検出された問題, 文章\n")
        cflag = False
        for line_number, line in enumerate(file, start=1):
            line = line.strip()
            if len(line) == 0:
                continue
            if line.startswith(r"\end{document}"): break
            if line.startswith("%") or line.startswith("\\") or "助成" in line:
                if line.startswith("\\bibitem"):
                    bibflag = True
                cflag = False
                continue
            # cflagがTrueであれば、前の行と現在の行を結合
            if cflag:
                line = previous_line + line
                line_number = previous_number
                cflag = False
            # 文が句点で終わらない場合に、次の行と結合するための準備
            if not line.endswith("。") and not line.endswith("．"):
                previous_line = line
                previous_number = line_number
                cflag = True
                continue
            else:
                # 文が句点で終わっている場合は、cflagをFalseにして、次の行で結合しないようにする
                if cflag:
                    cflag = False
            for name, pattern in patterns.items():
                if (
                    name != "半角文字と参考文献の間に半角スペースがない"
                    and name != "句点の後に参考文献"
                ):
                    clean_line = re.sub(r"\\\w+\{[^}]*\}", "", line)
                    clean_line = re.sub(r"\$[^$]*\$", "", clean_line)
                else:
                    clean_line = line
                search = re.search(pattern, clean_line)
                if search:
                    if name == "4桁以上の数字にカンマがない" and (bibflag or bool(re.match(r"^(19[0-9]{2}|20[0-9]{2})$", search.group()))):
                        continue
                    output_result(output_file, line, line_number, name, results)
            if bibflag and line.endswith("."):
                bibflag = False


def process_file(input_file_path, output_file_path, results):
    # 関数を実行
    find_and_save_patterns(input_file_path, output_file_path, patterns, results)
    pass


if __name__ == "__main__":
    app.run(debug=True)
