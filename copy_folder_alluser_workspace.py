#command: python3 copy_folder_alluser_workspace.py --users_file user.txt
import subprocess
import click
@click.command()
@click.option('--users_file', '-u', required=True, type=click.Path(exists=True),
              help='Path to the file containing questions.')
@click.option('--loc', '-loc', required=False, type=click.Path(exists=True),
              help='Path to the file containing questions.')
@click.option('--source', '-source', required=False, type=click.Path(exists=True),
              help='Path to the file containing questions.')
def main(users_file,loc,source):
    with open(users_file, 'r') as file:
        users = [line.strip() for line in file if line.strip()]
    print(type(loc))
    print(f"loc={loc}")
    if loc == None:
        loc = "docs"
    if source == None:
        source = "/home/data/contract"
    destination = []
    for user in users:
        destination.append(f"/home/{user}/{loc}")
    print(f"destination: {destination}")
    for des in destination:
        command = [f"sudo mkdir {des}"]
        subprocess.run(command,shell=True)
        command1 = [f"sudo cp -r {source} {des}"]
        r = subprocess.run(command1,shell=True)
        print(r)

if __name__ == "__main__":
    main()
