with open('interaction_log.txt', 'r') as file:
    contents = file.readlines()
    for line in contents:
        print(line.strip())
