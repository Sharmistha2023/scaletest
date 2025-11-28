import subprocess
command = "d3x dataset list | awk '{print $4}'"


with open('/home/sharmistha-choudhury/fil1.txt', 'r') as file:
	questions = [line.strip() for line in file if line.strip()]
for i in questions:
	command = f"d3x dataset delete -d {i} -p"
	subprocess.run(command,shell=True)
