from tinkertool.scripts.postprocess.config import ReshapeRechunkConfig
from tinkertool.scripts.postprocess.reshape_rechunk import reshape_and_rechunk


def reshape_ppe_CLI():
    config = ReshapeRechunkConfig.from_cli()  # type: ignore
    reshape_and_rechunk(config)


if __name__ == "__main__":
    reshape_ppe_CLI()
