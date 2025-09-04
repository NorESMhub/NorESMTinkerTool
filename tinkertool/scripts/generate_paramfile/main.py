from tinkertool.scripts.generate_paramfile.cli import parse_cli_args
from tinkertool.scripts.generate_paramfile.config import ParameterFileConfig
from tinkertool.scripts.generate_paramfile.generate_paramfile import generate_paramfile

def main():
    config: ParameterFileConfig = parse_cli_args()
    generate_paramfile(config)

if __name__ == "__main__":
    main()