import sys
import argparse
from markdownparser import MarkdownParser


def parse_arguments():
    parser = argparse.ArgumentParser(description="convert markdown to html")
    parser.add_argument('input', help='input markdown file')
    parser.add_argument('output', help='output html file',
                        default='result.html')
    parser.add_argument('--template', help='html template file', default=None)
    return parser.parse_args()


def main():
    if len(sys.argv) < 1:
        print("Usage: ./markdownparser <input_file> <output_file>")
        sys.exit(1)

    args = parse_arguments()
    parser = MarkdownParser()
    success = parser.convert_file(args.input, args.output, args.template)
    print("Converted!" if success else "Failed to convert")


if __name__ == "__main__":
    main()
