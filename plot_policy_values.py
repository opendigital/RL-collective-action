# libraries
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import json

NUM_AGENTS = 17
NAME = 'MADDPG Cooperative Sum State'
FILENAME = NAME.replace(' ', '').lower()

def get_policy_means(filename):
    f = open(filename, "r")
    result = [json.loads(line) for line in f]
    f.close()

    return result

def split_obj_into_array(objects):
    result = [[] for i in range(NUM_AGENTS)]

    for obj in objects:
        for i in range(NUM_AGENTS):
            key = 'agent-' + str(i)
            result[i].append(obj[key])
    
    return result

objects = get_policy_means(FILENAME + "_policymeans.txt")
arr = split_obj_into_array(objects)

for i in range(len(arr)):
    plt.plot(arr[i])

plt.xlabel('Iteration')
plt.ylabel('Reward')
plt.title(NAME + ' Rewards')
plt.savefig('charts/' + FILENAME + '_policymeanschart.png')

# Data
# df=pd.DataFrame({'x_values': range(1, 50001), 'y1_values': np.random.randn(10), 'y2_values': np.random.randn(10)+range(1,11), 'y3_values': np.random.randn(10)+range(11,21) })
