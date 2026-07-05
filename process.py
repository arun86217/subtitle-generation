import argparse

from dotenv import load_dotenv

from subtitle_gen.environment import Environment
from subtitle_gen.logger import Logger
from subtitle_gen.media_tools import MediaTools
from subtitle_gen.transcriber import Transcriber
from subtitle_gen.pipeline import SubtitlePipeline

load_dotenv()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--language", default="en")
    return parser.parse_args()


def main():
    args = parse_args()

    environment = Environment()
    environment.validate()

    logger = Logger()
    media_tools = MediaTools(environment, logger)
    transcriber = Transcriber(environment.model_path, logger)

    pipeline = SubtitlePipeline(environment, logger, media_tools, transcriber)
    pipeline.run(args.input, args.output, args.resume, args.language)


if __name__ == "__main__":
    main()
