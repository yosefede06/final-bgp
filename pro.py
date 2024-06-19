from BGPDump import BGPDump
import os
import requests
import csv
import time
from datetime import datetime, timedelta
from collections import defaultdict
import pickle
import threading
import queue


def save_dictionaries(filename, *dictionaries):
    with open(filename, 'wb') as f:
        pickle.dump(dictionaries, f)


def load_dictionaries(filename):
    if os.path.exists(filename):
        with open(filename, 'rb') as f:
            return pickle.load(f)
    else:
        return None


def default_inner_dict():
    return {"last_path": "", "changed_recently": False, "paths_set": set()}


def default_outer_dict():
    return defaultdict(default_inner_dict)


collector = "rrc00"
destination_folder = "./mrt_files"
output_csv_max = f'output_ipv4_max_{collector}.csv'
output_csv_changes = f'output_ipv4_changes_{collector}.csv'
collectors_metadata = defaultdict(default_outer_dict)
max_counts = []
change_counts = []
pickle_file = 'data.pkl'  # File to save dictionaries
file_queue = queue.Queue(maxsize=10)  # Ensure only 10 files are queued for processing



def process_mrt_file():
    while True:
        local_filename, index, time_curr, start_time = file_queue.get()
        if local_filename is None:
            break
        with open(output_csv_max, 'a', newline='') as csvfile_max, \
                open(output_csv_changes, 'a', newline='') as csvfile_changes:
            csv_writer_max = csv.writer(csvfile_max)
            csv_writer_changes = csv.writer(csvfile_changes)
            mrt_file = local_filename
            changes = defaultdict(int)
            test_dict = {}
            with BGPDump(mrt_file) as bgp:
                for entry in bgp:
                    if entry.attr and entry.attr.asPath and entry.body.announce:
                        as_path = entry.attr.asPath
                        peer_as = int(entry.body.sourceAS)
                        for prefix in entry.body.announce:
                            entry_data = collectors_metadata[peer_as][prefix]
                            paths_set = entry_data["paths_set"]
                            has_changed = entry_data["last_path"] != as_path
                            if has_changed and not entry_data["changed_recently"] and paths_set:
                                if peer_as == 49134:
                                    # print(f"Old: {entry_data['last_path']}")
                                    # print(f"New: {as_path}")
                                    pass
                                changes[peer_as] += 1
                                entry_data["changed_recently"] = True
                            paths_set.add(as_path)
                            entry_data["paths_set"] = paths_set
                            entry_data["last_path"] = as_path
                    if entry.body.withdraw:
                        for prefix in entry.body.withdraw:
                            peer_as = int(entry.body.sourceAS)
                            entry_data = collectors_metadata[peer_as][prefix]
                            if not entry_data["changed_recently"] and entry_data["paths_set"]:
                                changes[peer_as] += 1
                                entry_data["changed_recently"] = True
                            entry_data["last_path"] = ""
            print(f"Prefixes: {len(collectors_metadata[49134])}")
            print(f"Changes: {changes[49134]}")
            max_processed_data = ProcessingStrategies.max_paths(collectors_metadata)
            # csv_writer_max.writerow([index, time_curr, *max_processed_data])
            #
            # csv_writer_changes.writerow([index, time_curr, *changes.items()])

            max_counts.append(max_processed_data[1])
            change_counts.append(changes)

            os.remove(mrt_file)

            # Reset changed_recently flag for the next batch
            for peer_as in collectors_metadata:
                for prefix in collectors_metadata[peer_as]:
                    collectors_metadata[peer_as][prefix]["changed_recently"] = False

        end_time = time.time()
        print(f"File {local_filename} processed in {end_time - start_time:.2f} seconds")
        file_queue.task_done()


def download_file(url, destination_folder):
    local_filename = os.path.join(destination_folder, url.split('/')[-1])
    with requests.get(url, stream=True) as r:
        if r.status_code == 200:
            with open(local_filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        else:
            print(f"Failed to download {url}")
    return local_filename


class ProcessingStrategies:
    @staticmethod
    def max_paths(metadata):
        max_values = []
        for outer_key, inner_dict in metadata.items():
            max_len = 0
            max_outer_key = outer_key
            for entry_data in inner_dict.values():
                length = len(entry_data["paths_set"])
                if length > max_len:
                    max_outer_key = outer_key
                    max_len = length
            max_values.append((max_outer_key, max_len))
        return max_values


def download_and_process():
    count_index = 1
    rrc_number = '00'  # Set the RRC number here
    base_url = f"https://data.ris.ripe.net/rrc{rrc_number}"

    start_date = datetime(2023, 1, 1, 21, 0)  # Start date and time
    end_date = datetime(2023, 2, 1, 0, 0)  # End date and time
    delta = timedelta(minutes=5)

    os.makedirs(destination_folder, exist_ok=True)
    for filename in os.listdir(destination_folder):
        if filename.endswith('.gz'):
            os.remove(os.path.join(destination_folder, filename))

    current_date = start_date

    # Start the processing thread
    processing_thread = threading.Thread(target=process_mrt_file)
    processing_thread.start()

    while current_date < end_date:
        filename = f"updates.{current_date.strftime('%Y%m%d.%H%M')}.gz"
        url = f"{base_url}/{current_date.year}.{current_date.strftime('%m')}/{filename}"
        print(f"Downloading {url}")
        start_time = time.time()
        local_filename = download_file(url, destination_folder)
        file_queue.put((local_filename, count_index, current_date.strftime("%Y-%m-%d %H:%M:%S"), start_time))

        current_date += delta
        count_index += 1

    # Signal the processing thread to stop
    file_queue.put((None, None, None, None))
    processing_thread.join()

    # Save dictionaries at the end of the download
    save_dictionaries(pickle_file, collectors_metadata, max_counts, change_counts)


if __name__ == "__main__":
    collector = "rrc00"
    destination_folder = "./mrt_files"
    # Load dictionaries if they exist
    # loaded_dictionaries = load_dictionaries(pickle_file)
    # if loaded_dictionaries:
    #     collectors_metadata, max_counts, change_counts = loaded_dictionaries
    # else:
    #     os.remove(output_csv_max) if os.path.exists(output_csv_max) else None
    #     os.remove(output_csv_changes) if os.path.exists(output_csv_changes) else None
    download_and_process()