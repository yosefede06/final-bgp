import csv
import matplotlib.pyplot as plt
from collections import defaultdict
import re
import pandas as pd
from matplotlib.ticker import MaxNLocator
import matplotlib.dates as mdates


# Function to parse the AS paths
def parse_as_paths(as_paths):
    as_dict = defaultdict(list)
    for as_path in as_paths:
        match = re.match(r"\((\d+), (\d+)\)", as_path)
        if match:
            as_num = int(match.group(1))
            value = int(match.group(2))
            as_dict[as_num].append(value)
    return as_dict

# Read the CSV file and parse the data
csv_file = "output_ipv4_max_rrc00.csv"  # Replace with the path to your CSV file

data = []

with open(csv_file, newline='') as csvfile:
    reader = csv.reader(csvfile)
    for row in reader:
        snapshot = row[0]
        time = row[1]
        max_paths = row[2:]  # Assuming max paths start from the third column
        data.append((snapshot, time, parse_as_paths(max_paths)))

# Aggregate the data to find the top 10 AS values with the highest maximum paths
as_aggregate = defaultdict(list)

for snapshot, time, as_paths in data:
    for as_num, values in as_paths.items():
        as_aggregate[as_num].extend(values)

# Calculate the maximum value for each AS and get the top 10 AS values
top_as = sorted(as_aggregate.items(), key=lambda x: max(x[1]), reverse=True)[:10]

# Prepare data for plotting
top_as_numbers = [item[0] for item in top_as]
top_as_data = defaultdict(list)

for snapshot, time, as_paths in data:
    for as_num in top_as_numbers:
        if as_num in as_paths:
            top_as_data[as_num].append(max(as_paths[as_num]))
        else:
            top_as_data[as_num].append(0)  # If no data for this snapshot, append 0
df = pd.DataFrame(top_as_data, index=pd.to_datetime([time for _, time, _ in data]))

# Convert the data to a pandas DataFrame for easier plotting
# df = pd.DataFrame(top_as_data, index=pd.to_datetime([time.split()[0] for _, time, _ in data]))

# Plot the data
# plt.figure(figsize=(10, 6))
width_in_inches = 3.9  # 0.47 * typical LaTeX text width
height_in_inches = 3.7  # 0.37 * typical LaTeX text width

# Adjust font sizes
plt.rcParams.update({
    'axes.titlesize': 7,
    'axes.labelsize': 7,
    'xtick.labelsize': 7,
    'ytick.labelsize': 7,
    'legend.fontsize': 7,
    'legend.title_fontsize': 7
})

# Plot the data
plt.figure(figsize=(width_in_inches, height_in_inches))


for as_num in top_as_numbers:
    plt.plot(df.index, df[as_num], label=f'AS {as_num}')

plt.xlabel('Time')
plt.ylabel('Maximum Paths')
plt.title('Top 10 AS Peers by Max Unique Paths in RRC00 Over 1 Year')
plt.legend()

# Limit the number of x-ticks to 12
ax = plt.gca()
ax.xaxis.set_major_locator(MaxNLocator(nbins=12))
# ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
plt.xticks(rotation=45)

plt.tight_layout()

# Save the plot as a PNG file
plt.savefig('top_10_max_paths.png')

# Save the plot as a LaTeX-compatible PGF file
plt.savefig('top_10_max_paths.pgf', bbox_inches='tight', pad_inches=0)

plt.show()