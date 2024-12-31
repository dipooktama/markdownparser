import re
import sys
from pathlib import Path


class MarkdownParser:
    def __init__(self):
        self.patterns = {
            'header': re.compile(r'^(#{1,6})\s(.+)$'),
            'bold': re.compile(r'\*\*(.+?)\*\*'),
            'italic': re.compile(r'\*(.+?)\*'),
            'link': re.compile(r'\[(.+?)\]\((.+?)\)'),
            'image': re.compile(r'\!\[(.+?)\]\((.+?)\)'),
            'code_block': re.compile(r'```(.*?)\n(.*?)```', re.DOTALL),
            'inline_code': re.compile(r'`(.*?)`'),
            'unordered_list': re.compile(r'^(\s*)[-*]\s(.+)$'),
            'ordered_list': re.compile(r'^(\s*)(\d+)\.\s(.+)$'),
        }
        self.current_list_stack = []

    def parse_line(self, line: str):
        header_match = self.patterns['header'].match(line)
        if header_match:
            level = len(header_match.group(1))
            return f'<h{level}>{self.parse_inline(header_match.group(2))}</h{level}>'

        ul_match = self.patterns['unordered_list'].match(line)
        ol_match = self.patterns['ordered_list'].match(line)

        if ul_match or ol_match:
            indent = len(ul_match.group(1)) if ul_match else len(
                ol_match.group(1))
            content = ul_match.group(2) if ul_match else ol_match.group(3)
            is_ordered = bool(ol_match)

            html = []
            while self.current_list_stack and self.current_list_stack[-1][0] > indent:
                list_type = 'ol' if self.current_list_stack[-1][1] else 'ul'
                html.append(f'</{list_type}>')
                self.current_list_stack.pop()

            if not self.current_list_stack or self.current_list_stack[-1][0] < indent:
                list_type = 'ol' if is_ordered else 'ul'
                html.append(f'<{list_type}>')
                self.current_list_stack.append((indent, is_ordered))

            # Add list item
            html.append(f'<li>{self.parse_inline(content)}</li>')
            return '\n'.join(html)

        # If we were in a list and hit a non-list line, close all lists
        if self.current_list_stack:
            html = []
            while self.current_list_stack:
                list_type = 'ol' if self.current_list_stack[-1][1] else 'ul'
                html.append(f'</{list_type}>')
                self.current_list_stack.pop()
            return '\n'.join(html) + '\n' + self.parse_inline(line)

        return self.parse_inline(line) if line.strip() else ''

    def parse_inline(self, text: str):
        text = self.patterns['bold'].sub(
            r'<strong>\1</strong>', text)  # parse bold
        text = self.patterns['italic'].sub(
            r'<em>\1</em>', text)  # parse italic
        text = self.patterns['link'].sub(
            r'<a href="\2">\1</a>', text)  # parse link
        text = self.patterns['image'].sub(
            r'<img src="\2" alt="\1">\1</img>', text)  # parse image
        text = self.patterns['inline_code'].sub(
            r'<code>\1</code>', text)  # parse inline code
        return text

    def parse_blocks(self, text: str):
        blocks = []
        current_block = []
        in_code_blocks = False
        code_content = []

        for line in text.split("\n"):
            if line.startswith('```'):
                if not in_code_blocks:
                    in_code_blocks = True
                    language = line[3:].strip()
                else:
                    blocks.append(
                        f'<pre><code class="language-{language}">\n'
                        f'{"\n".join(code_content)}\n</code></pre>'
                    )
                    code_content = []
                    in_code_blocks = False
                continue

            if in_code_blocks:
                code_content.append(line)
                continue

            if line.strip() == '':
                if current_block:
                    content = ' '.join(current_block)
                    if not content.startswith('<h') and not content.startswith('<ol') and not content.startswith('<ul'):
                        content = f'<p>{content}</p>'
                    blocks.append(content)
                    current_block = []
            else:
                parsed_line = self.parse_line(line)
                if parsed_line:
                    current_block.append(parsed_line)

        if current_block:
            content = ' '.join(current_block)
            if not content.startswith('<h') and not content.startswith('<ol') and not content.startswith('<ul'):
                content = f'<p>{content}</p>'
            blocks.append(content)

        return '\n'.join(blocks)

    def convert_file(self, input_path: str, output_path: str):
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                markdown_content = f.read()

            html_content = self.parse_blocks(markdown_content)

            # html template
            html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{Path(input_path).stem}</title>
    <link rel="stylesheet" href="./styles/style.css" />
</head>
<body>
    {html_content}
</body>
</html>"""

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_doc)
            return True

        except Exception as e:
            print(f'Error: {str(e)}')
            return False


def main():
    if len(sys.argv) != 3:
        print("Usage: ./markdownparser <input_file> <output_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    parser = MarkdownParser()
    success = parser.convert_file(input_file, output_file)
    print("Converted!" if success else "Failed to convert")


if __name__ == "__main__":
    main()
