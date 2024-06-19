# Run Python 3.10 example.py
from BGPDump import BGPDump
import os
import requests
import csv
import time
from datetime import datetime, timedelta
from collections import defaultdict
from operator import itemgetter
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

def default_dict_set():
    return defaultdict(set)

collector = "rrc00"
destination_folder = "./mrt_files"
output_csv_max = f'output_ipv4_max_{collector}.csv'
output_csv_avg = f'output_ipv4_avg_{collector}.csv'
collectors_metadata = defaultdict(default_dict_set)
max_counts = []
avg_counts = []  # Store average counts as well
batch_labels = []
pickle_file = 'data.pkl'  # File to save dictionaries
file_queue = queue.Queue(maxsize=10)  # Ensure only 10 files is queued for processing

def process_mrt_file():
    while True:
        local_filename, index, time_curr, start_time = file_queue.get()
        if local_filename is None:
            break
        with open(output_csv_avg, 'a', newline='') as csvfile_avg:
            with open(output_csv_max, 'a', newline='') as csvfile_max:
                csv_writer_max = csv.writer(csvfile_max)
                csv_writer_avg = csv.writer(csvfile_avg)
                mrt_file = local_filename
                with BGPDump(mrt_file) as bgp:
                    for entry in bgp:
                        if entry.attr and entry.attr.asPath and entry.body.announce:
                            as_path = entry.attr.asPath
                            peer_as = entry.body.sourceAS
                            for prefix in entry.body.announce:

                                collectors_metadata[peer_as][prefix].add(str(as_path))
                max_processed_data = ProcessingStrategies.max_paths(collectors_metadata)
                avg_processed_data = ProcessingStrategies.average_paths(collectors_metadata)
                csv_writer_max.writerow([index, time_curr, *max_processed_data])
                csv_writer_avg.writerow([index, time_curr, *avg_processed_data])
                max_counts.append(max_processed_data[1])
                avg_counts.append(avg_processed_data[1])
                os.remove(mrt_file)
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
    def average_paths(metadata):
        averages = [(outer_key, round(sum(len(value) for value in inner_dict.values()) / len(inner_dict), 2))
                    for outer_key, inner_dict in metadata.items()]
        return averages
        # max_entry = max(averages, key=itemgetter(1))
        # return *max_entry, len(metadata[max_entry[0]])

    @staticmethod
    def max_paths(metadata):
        maximum = [(outer_key, max([len(value) for value in inner_dict.values()]))
                    for outer_key, inner_dict in metadata.items()]
        return maximum
        # max_entry = max(maximum, key=itemgetter(1))
        # return *max_entry, len(metadata[max_entry[0]])

def download_and_process():
    cumulative_time = 0
    count_index = 1
    rrc_number = '00'  # Set the RRC number here
    base_url = f"https://data.ris.ripe.net/rrc{rrc_number}"

    start_date = datetime(2023, 1, 1, 0, 0)  # Start date and time
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
    save_dictionaries(pickle_file, collectors_metadata, max_counts, avg_counts)

if __name__ == "__main__":
    collector = "rrc00"
    destination_folder = "./mrt_files"
    # Load dictionaries if they exist
    loaded_dictionaries = load_dictionaries(pickle_file)
    if loaded_dictionaries:
        collectors_metadata, max_counts, avg_counts = loaded_dictionaries
    else:
        os.remove(output_csv_avg) if os.path.exists(output_csv_avg) else None
        os.remove(output_csv_max) if os.path.exists(output_csv_max) else None
    download_and_process()
