from tinkertool.scripts.generate_paramfile.config import ParameterFileConfig
from tinkertool.scripts.generate_paramfile.generate_paramfile import generate_paramfile


def main():
    config = ParameterFileConfig.from_cli()    # type: ignore  # Suppress Pylance warning
    generate_paramfile(config)


if __name__ == "__main__":
    main()
