import argparse
import getpass
import sys
from typing import Sequence

from ._client import Client


def main(argv: Sequence[str] = sys.argv) -> None:
    args = parse_args(argv)
    client = get_client(args)
    with client.connect() as connection:
        if args.check_only:
            for pupil in connection.pupils.values():
                count = connection.new_message_counts.get(pupil.id, 0)
                print(f'{pupil.name}: {count}')
        elif args.list:
            for (n, pupil) in enumerate(connection.pupils.values()):
                if n != 0:
                    print('')
                print(f'Pupil: {pupil.name}')
                message_infos = connection.fetch_message_list(pupil.id)
                for message_info in message_infos:
                    print(message_info)
        else:
            new_messages = connection.get_new_messages()
            for (n, pupil) in enumerate(new_messages.keys()):
                print(f'Pupil: {pupil.name}')
                print('')
                for message in new_messages[pupil]:
                    print(message)
                    print('')


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog=argv[0])
    parser.add_argument(
        '--url', '-U', required=True,
        help="Base URL for the connection")
    parser.add_argument(
        '--username', '-u', required=False,
        help="Username to login as")
    # parser.add_argument(
    #     '--password', '-p', type=str,
    #     help="Password for the login")
    parser.add_argument(
        '--check-only', '-c', action='store_true',
        help="Only check if there is new messages available")
    parser.add_argument(
        '--list', '-l', action='store_true',
        help="List message headers")
    return parser.parse_args(argv[1:])


def get_client(args: argparse.Namespace) -> Client:
    username = (args.username or input('Username: '))
    password = getpass.getpass()
    return Client(args.url, username, password)


if __name__ == '__main__':
    main()
