import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Tuple, Dict


class MarkdownParser:
    def __init__(self):
        self.patterns = {
            'header': re.compile(r'^(#{1,6})\s(.+)$'),
            'bold': re.compile(r'\*\*(.+?)\*\*'),
            'italic': re.compile(r'\*(.+?)\*'),
            'link': re.compile(r'\[(.+?)\]\((.+?)\)'),
            'image': re.compile(r'\!\[(.+?)\]\((.+?)\)'),
            'code_block': re.compile(r'```(]w*)\n(.*?)```', re.DOTALL),
            'inline_code': re.compile(r'`(.*?)`'),
            'unordered_list': re.compile(r'^(\s*)[-*]\s(.+)$'),
            'ordered_list': re.compile(r'^(\s*)(\d+)\.\s(.+)$'),
            'metadata': re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL),
        }
        self.current_list_stack = []

    def parse_metadata(self, text: str) -> Tuple[Dict[str, str], str]:
        """Parse metadata"""
        metadata = {}
        content = text

        metadata_match = self.patterns['metadata'].match(text)
        if metadata_match:
            metadata_block = metadata_match.group(1)
            content = text[metadata_match.end():]

            # Parse each line of metadata
            for line in metadata_block.strip().split('\n'):
                line = line.strip()
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    # Remove quotes if they exist
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    metadata[key] = value

        return metadata, content

    def parse_line(self, line: str):
        header_match = self.patterns['header'].match(line)
        if header_match:
            level = len(header_match.group(1))
            headersize = 'text-6xl' if level == 1 else 'text-4xl' if level == 2 else 'text-2xl'
            headercolor = 'text-red-900'
            headerstyle = f'{headersize} {
                headercolor} mb-5 font-black uppercase'
            return f'<h{level} class="{headerstyle}">{self.parse_inline(header_match.group(2))}</h{level}>'

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
                liststyle = 'list-decimal list-inside' if list_type == 'ol' else 'list-disc list-inside'
                html.append(f'<{list_type} class="{liststyle}">')
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
            r'<strong class="font-bold">\1</strong>', text)  # parse bold
        text = self.patterns['italic'].sub(
            r'<em class="italic">\1</em>', text)  # parse italic
        text = self.patterns['image'].sub(
            r'<img src="\2" alt="\1" />', text)  # parse image
        text = self.patterns['link'].sub(
            r'<a href="\2" class="underline">\1</a>', text)  # parse link
        text = self.patterns['inline_code'].sub(
            r'<code class="bg-slate-300">\1</code>', text)  # parse inline code
        return text

    def parse_blocks(self, text: str) -> Tuple[Dict[str, str], str]:
        metadata, contentz = self.parse_metadata(text)

        blocks = []
        current_block = []
        in_code_blocks = False
        code_content = []
        paragraphstyle = "mb-5 text-justify"

        lines = contentz.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i]

            # Handle code blocks
            if line.startswith('```'):
                # Close any open lists before starting a code block
                if self.current_list_stack:
                    if current_block:
                        content = ' '.join(current_block)
                        blocks.append(content)
                        current_block = []

                    closing_tags = []
                    while self.current_list_stack:
                        list_type = 'ol' if self.current_list_stack[-1][1] else 'ul'
                        closing_tags.append(f'</{list_type}>')
                        self.current_list_stack.pop()
                    blocks.append('\n'.join(closing_tags))

                if not in_code_blocks:
                    if current_block:
                        content = ' '.join(current_block)
                        if not content.startswith(('<h', '<ol', '<ul')):
                            content = f'<p class="{
                                paragraphstyle}">{content}</p>'
                        blocks.append(content)
                        current_block = []

                    in_code_blocks = True
                    language = line[3:].strip()
                    i += 1
                    continue
                else:
                    blocks.append(
                        f'<pre>\n  <code class="language-{language}">\n    '
                        f'{"\n    ".join(code_content)}\n  </code>\n</pre>'
                    )
                    code_content = []
                    in_code_blocks = False
                    i += 1
                    continue

            if in_code_blocks:
                code_content.append(line)
                i += 1
                continue

            next_line_is_list = False
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                next_line_is_list = bool(self.patterns['unordered_list'].match(next_line) or
                                         self.patterns['ordered_list'].match(next_line))

            # Handle regular content
            if line.strip() == '':
                if current_block:
                    content = ' '.join(current_block)
                    if not content.startswith(('<h', '<ol', '<ul')):
                        content = f'<p class="{paragraphstyle}">{content}</p>'
                    blocks.append(content)
                    current_block = []

                    # Close lists if next line is not a list
                    if self.current_list_stack and not next_line_is_list:
                        closing_tags = []
                        while self.current_list_stack:
                            list_type = 'ol' if self.current_list_stack[-1][1] else 'ul'
                            closing_tags.append(f'</{list_type}>')
                            self.current_list_stack.pop()
                        blocks.append('\n'.join(closing_tags))
            else:
                parsed_line = self.parse_line(line)
                if parsed_line:
                    if parsed_line.startswith(('<ol', '<ul')) and current_block:
                        # Flush current block before starting a list
                        content = ' '.join(current_block)
                        if not content.startswith(('<h', '<ol', '<ul')):
                            content = f'<p class="{
                                paragraphstyle}">{content}</p>'
                        blocks.append(content)
                        current_block = []
                    current_block.append(parsed_line)
            i += 1

        # Handle any remaining content
        if current_block:
            content = ' '.join(current_block)
            if not content.startswith(('<h', '<ol', '<ul')):
                content = f'<p class="{paragraphstyle}">{content}</p>'
            blocks.append(content)

        # Close any remaining open lists
        if self.current_list_stack:
            closing_tags = []
            while self.current_list_stack:
                list_type = 'ol' if self.current_list_stack[-1][1] else 'ul'
                closing_tags.append(f'</{list_type}>')
                self.current_list_stack.pop()
            blocks.append('\n'.join(closing_tags))

        formatted_blocks = []
        # parse metadata into html
        if metadata:
            datetimeval = metadata.get('datetime')

            if not datetimeval:
                timezone_offset = 7.0  # GMT+7 aka indo
                tzinfo = timezone(timedelta(hours=timezone_offset))
                parsed_at = datetime.now(tzinfo)
                datetimeval = parsed_at.strftime('%Y-%m-%d %H:%M:%S')

            author_part = f'<p class="text-xs text-slate-500">Written by {
                metadata.get('author')}</p>'
            created_at = f'<p class="text-xs text-slate-500">at {
                datetimeval}</p>'
            updated_at = f'<p class="text-xs text-slate-500">edited at {
                metadata.get('updatetime')}</p>' if metadata.get('updatetime') else None
            section_datetime = f'<section class="flex flex-row gap-x-4">{
                created_at + "\n" + updated_at if updated_at else created_at}</section>'
            formatted_blocks.append(
                f'<section class="flex flex-row justify-between mb-5">{author_part + "\n" + section_datetime}</section>')

        # Format the final HTML with proper indentation
        for block in blocks:
            lines = block.split('\n')
            formatted_lines = []
            for line in lines:
                if line.startswith(('</ol>', '</ul>')):
                    formatted_lines.append('  ' + line)
                elif line.startswith(('<li', '</li>')):
                    formatted_lines.append('    ' + line)
                else:
                    formatted_lines.append('  ' + line)
            formatted_blocks.append('\n'.join(formatted_lines))

        return metadata, '\n'.join(formatted_blocks)

    def convert_file(self, input_path: str, output_path: str, template_path: Optional[str] = None) -> bool:
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                markdown_content = f.read()

            metadata, html_content = self.parse_blocks(markdown_content)
            if template_path:
                final_html = self.apply_template(
                    template_path=template_path,
                    title=metadata.get('title', Path(input_path).stem),
                    content=html_content,
                    metadata=metadata
                )
            else:
                final_html = self.create_default_html(
                    title=metadata.get('title', Path(input_path).stem),
                    content=html_content,
                    metadata=metadata
                )

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(final_html)
            return True

        except Exception as e:
            print(f'Error: {str(e)}')
            return False

    def apply_template(self, template_path: str, title: str, content: str, metadata: Dict[str, str]) -> str:
        try:
            template = Path(template_path).read_text(encoding='utf-8')
            template = template.replace('{{title}}', title)

            if '{{content}}' not in template:
                raise ValueError(
                    'Template must contain {{content}} mark in the body')

            # Replace any metadata variables
            for key, value in metadata.items():
                template = template.replace('{{'+key+'}}', value)

            return template.replace('{{content}}', content)
        except FileNotFoundError:
            raise FileNotFoundError(
                f'Template file not found: {template_path}')
        except Exception as e:
            raise Exception(f'Error applying template: {str(e)}')

    @staticmethod
    def create_default_html(title: str, content: str) -> str:
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link rel="stylesheet" href="./styles/style.css" />
</head>
<body>
    {content}
</body>
</html>"""
