import argparse
import tiktoken

def parse_arguments():
    parser = argparse.ArgumentParser(description='Get a quick token count on a file using tiktoken')
    parser.add_argument('-i', '--input', required=True,
                        help='Path to the input file for token count.')
    parser.add_argument('--encoding-name', default='o200k_base',
                        help='The tiktoken encoding name to use for tokenization (default: o200k_base).')
    return parser.parse_args()

def count_tokens(file_path, encoding):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            text = file.read()
            tokens = encoding.encode(text)
            return len(tokens)
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        return None
    except Exception as e:
        print(f"Error reading file: {e}")
        return None

def main():
    args = parse_arguments()
    
    # Initialize tiktoken encoding
    try:
        encoding = tiktoken.get_encoding(args.encoding_name)
    except Exception as e:
        print(f"Error initializing tiktoken encoding '{args.encoding_name}': {e}")
        return
    
    # Count tokens
    token_count = count_tokens(args.input, encoding)
    
    if token_count is not None:
        print(f"Number of tokens in {args.input}: {token_count}")

if __name__ == '__main__':
    main()
