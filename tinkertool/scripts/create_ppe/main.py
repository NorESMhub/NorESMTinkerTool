from tinkertool.scripts.create_ppe.cli import parse_cli_args
from tinkertool.scripts.create_ppe.create_ppe import create_ppe

def main():
    config = parse_cli_args()
    create_ppe(config)

if __name__ == "__main__":
    main()