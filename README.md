# ML API Documentation
ML-API is a flask based API implemented to analyze instagram accounts using machine learning techniques. The main components of the system includes a grab script, a scrape script and an analysis script.

Once an account is submitted for analysis, the following process is executed:

Step 1: Grab followers of account using the grab script
Step 2: Scrape details of the followers grabbed in step 1, using the scrape script
Step 3: Perform machine learning analysis on the scraped data using the predict script and persist results to an sqlite3 database
Deployment
This section outlines the steps that should be followed to deploy the ML-API in a server, pre-configured with python3.6.

To start, clone the following repository: https://github.com/priyath/insta-machine-learning. For the purpose of this documentation, assume the cloned location in the server is /home/forge/insta-machine-learning/
## 1. Torrc - Privoxy configuration
The scrape script proxies its requests through multiple tor circuits to avoid IP bans from Instagram servers. Therefore, the server should be configured to run multiple tor circuits with periodic IP rotation.

1. Install Tor and Privoxy

sudo apt-get update
sudo apt-get install privoxy
sudo apt-get install tor

2. Setup the config files for both Tor and Privoxy by executing the setup.sh script found within the scripts directory of the cloned repository.
Note: you may require sudo access to perform this step and provide permission to the scripts like so chmod +x setup.sh

3. Run the start.sh script to initialize the tor circuits for the server.

4. To verify that the tor circuit is up and running with IP rotation, execute the following curl command periodically and observe the change in the returned IP address.
curl --socks5 127.0.0.1:9i50 http://checkip.amazonaws.com/
Note: i = 0,1,2,3,4,5,6,7,8,9 for the 10 tor circuits configured through the setup.sh script.

## 2. API Setup
SSH into the server using a user with sudo access and perform the following operations.


0. Configure access permissions to the server using Uncomplicated Firewall

sudo apt install ufw
sudo ufw default allow outgoing
sudo ufw default deny incoming
sudo ufw allow ssh
sudo ufw allow 5000
sudo ufw allow 9181
sudo ufw enable
sudo ufw status

1. Install python virtual environment

sudo apt install python-venv

2. Create virtual environment inside our ML-API project

python3 -m venv /home/forge/insta-machine-learning/venv

This should create a venv folder inside the insta-machine-learning project folder.

3. Activate the virtual environment

source venv/bin/activate

4. Install project dependencies using the requirements.txt file. User should cd into the insta-machine-learning directory.

pip3 install -r requirements.txt

5. Cd into the database directory and create the sqlite3 database for the system


cat schema.sql | sqlite3 mlinsta.db

6. Install supervisor. Supervisor is a client-server system that allows us to control our python processes easily.

sudo apt-get install supervisor

7. Copy the mlapi.conf file inside the config folder to the supervisor config directory at /etc/supervisor/conf.d/. This config file controls the api, grab, scrape and predict processes of our system.

cp /home/forge/insta-machine-learning/config/mlapi.conf  /etc/supervisor/conf.d/

8. Install our web server, nginx

sudo apt install nginx

9. Install gunicorn which will handle our python code in the server

pip3 install gunicorn


10. Remove the default nginx configuration file and copy the mlapi file inside the config folder to the location shown below.

sudo rm /etc/nginx/sites-enabled/default
sudo cp  /home/forge/insta-machine-learning/config/mlapi  /etc/nginx/sites-enabled/

Note: You will need to change the server_name value to the IP address of the new server

11. Restart the nginx server and initialize supervisor

sudo systemctl restart nginx
sudo supervisorctl restart

12. Perform a curl to the health check endpoint to ensure the API is up and running


http://104.248.30.212:5000/
