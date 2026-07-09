import argparse
import json
import sys
from .runtime import run_engine
from .receipt import format_receipt

def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('task')
    args = parser.parse_args(argv)
    result = run_engine(args.task)
    print(format_receipt(result))
