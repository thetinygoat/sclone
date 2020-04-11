import click
from os import path, mkdir, _exit, listdir, makedirs, sep
from hashlib import sha256
from shutil import copy
import csv


class Backup:
    def __init__(self, source, destination, exclude):
        self.source = source
        self.exclude = exclude
        self.destination = destination
        self.first_run = True
        self.diff_file = path.join(destination, "diff_file.csv")
        self.file_list = []
        self.ignore_list = []
        self.hash_list = []
        self.backup_list = []
        # if not destination.endswith("/"):
        #     destination += "/"
        #     self.destination = destination
        # else:
        #     self.destination = destination

    def setup_destination(self):
        if path.exists(self.destination):
            return
        if path.exists(self.diff_file):
            self.first_run = False
            return
        mkdir(self.destination)
        with open(self.diff_file, "w") as f:
            fieldnames = ["path", "hash"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

    def generate_file_list(self):
        try:
            with open(self.exclude, "r") as f:
                self.ignore_list = [x.replace("\n", "") for x in f]
                for blob in listdir(self.source):
                    if ".*" in self.ignore_list and blob.startswith("."):
                        continue
                    if blob in self.ignore_list:
                        continue
                    self.file_list.append(path.join(self.source, blob))
        except IOError:
            print(f"error reading {self.exclude}")
            _exit(-1)

    def calc_hash(self, file):
        hash = sha256()
        with open(file, "rb") as f:
            for buffer in iter(lambda: f.read(4096), b""):
                hash.update(buffer)
        return hash.hexdigest()

    def generate_hash_list(self):
        for file in self.file_list:
            hash = self.calc_hash(file)
            self.hash_list.append((file, hash))

    def flush_hashes_to_diff(self):
        with open(self.diff_file, "w+") as f:
            fieldnames = ["path", "hash"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for pair in self.hash_list:
                writer.writerow({"path": pair[0], "hash": pair[1]})

    def create_backup_list(self):
        with open(self.diff_file, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                path = row["path"]
                old_hash = row["hash"]
                new_hash = self.calc_hash(path)
                if old_hash != new_hash:
                    self.backup_list.append(path)

    def construct_backup_path(self, file_path):
        file_path_array = file_path.split(sep)
        dest_path_array = self.destination.split(sep)
        for x in file_path_array:
            dest_path_array.append(x)
        dest_path = ""
        for x in dest_path_array:
            dest_path = path.join(dest_path, x)
        return dest_path

    def begin_backup(self):
        if self.first_run == True:
            for file_path in self.file_list:
                backup_path = self.construct_backup_path(file_path)
                print(backup_path)
                print("first run")
                makedirs(path.dirname(backup_path), exist_ok=True)
                copy(file_path, backup_path)
        else:
            for file_path in self.backup_list:
                backup_path = self.construct_backup_path(file_path)
                makedirs(path.dirname(backup_path), exist_ok=True)
                copy(file_path, backup_path)
        self.flush_hashes_to_diff()


@click.command()
@click.option("--source", help="Specify source")
@click.option("--destination", help="Specify destination")
@click.option("--exclude", help="specify a file containing files/folders to exclude")
def init(source, destination, exclude):
    backup = Backup(source, destination, exclude)
    backup.setup_destination()
    backup.generate_file_list()
    backup.generate_hash_list()
    backup.create_backup_list()
    backup.begin_backup()


if __name__ == "__main__":
    init()
