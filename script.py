import subprocess
import warnings

# Suppress MySQL warning about using passwords on the command line
warnings.filterwarnings("ignore", category=UserWarning, message=".*Using a password on the command line.*")

# Function to execute a shell command and get the output
def run_command(command):
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
    if result.returncode != 0:
        print(f"Error executing command: {result.stderr}")
        exit(1)
    return result.stdout

# Function to get the master status
def get_master_status(master_container):
    command = f'docker exec -i {master_container} mysql -u root -p1111 -e "SHOW MASTER STATUS;"'
    master_status = run_command(command)
    # Extract the master log file and position from the output
    lines = master_status.splitlines()
    if len(lines) < 2:
        print("Error: Could not retrieve master status.")
        exit(1)
    parts = lines[1].split()
    master_log_file = parts[0]
    master_log_pos = parts[1]
    return master_log_file, master_log_pos

# Function to reset and configure the slave replication
def configure_slave(slave_container, master_log_file, master_log_pos):
    print(f"Configuring slave {slave_container}...")
    # Correct the typo in the MySQL command (added space between mysql and -u)
    command = f"""docker exec -i {slave_container} mysql -u root -p1111 -e "
        STOP SLAVE;
        RESET SLAVE ALL;
        CHANGE MASTER TO 
            MASTER_HOST='mysql-master',
            MASTER_USER='replication_user',
            MASTER_PASSWORD='1111',
            MASTER_LOG_FILE='{master_log_file}',
            MASTER_LOG_POS={int(master_log_pos)},
            MASTER_SSL=0;
        START SLAVE;
    " """
    slave_status = run_command(command)
    print(slave_status)

# List of slave container names
slave_containers = ["mysql-slave-1", "mysql-slave-2", "mysql-slave-3"]

# Get the master status
master_log_file, master_log_pos = get_master_status("mysql-master")

for slave_container in slave_containers:
    configure_slave(slave_container, master_log_file, master_log_pos)

print("Replication reset and configuration completed.")
