from cli import parse_cli_args
from create_ppe import create_ppe

def main():
    config = parse_cli_args()
    create_ppe(config)

if __name__ == "__main__":
    main()