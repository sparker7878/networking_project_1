#import libs
from threading import Thread
import socket
from socket import AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
import time

current_round = 1
smth_changed_in_round = False

#socket for each node
socket_for_node = {}
dv_sender = 0
need_stop = False

def node_num_to_name(node_number):
    if node_number == 0:
        return 'A'
    if node_number == 1:
        return 'B'
    if node_number == 2:
        return 'C'
    if node_number == 3:
        return 'D'
    if node_number == 4:
        return 'E'

#wait for new message and check and update matrix 
def listen_thread(stop, node_number, current_dv_matrix):
    global smth_changed_in_round
    global socket_for_node

    node_name = node_num_to_name(node_number)
    sock = socket_for_node[node_number]
    sock.listen(1)
    while True:
        if stop():
            break

        try:
            socket.setdefaulttimeout(1)
            conn, client_address = sock.accept()
        except:
            continue

        msg = conn.recv(2000)
        if not msg:
            break

        nodes_info = msg.decode('ascii').split(" ")
        target_node = int(nodes_info[0])
        target_name = node_num_to_name(target_node)
        print("Node %s received DV from %s" % (node_name, target_name))

        dv_changed = False

        next_targets = nodes_info[1:]
        for targets in next_targets:
            target_num = int(targets.split(':')[0])
            weight = int(targets.split(':')[1])
            if (target_num == node_number):
                continue

            current_path = current_dv_matrix[target_node][target_node]
            possible_path = current_dv_matrix[target_num][target_node]
            current_path_to_target = current_path + weight

            if possible_path > current_path_to_target:
                dv_changed = True
                current_dv_matrix[target_num][target_node] = current_path_to_target
                print("Updating DV matrix at node %s" % node_name)
                print("New DV matrix at node %s = %s" % (node_name, str(current_dv_matrix)))

        if not dv_changed:
            print("No change in DV at node %s" % node_name)
        else:
            smth_changed_in_round = True
        conn.close()

    sock.close()


#thread
#999 infinity
def node_processor(node_number, neighbors, shortest_paths):
    global dv_sender
    global socket_for_node
    global current_round
    global smth_changed_in_round
    global need_stop

    current_dv_matrix = [ [999, 999, 999, 999, 999],
                  [999, 999, 999, 999, 999],
                  [999, 999, 999, 999, 999],
                  [999, 999, 999, 999, 999],
                  [999, 999, 999, 999, 999],
                  ]

    for n in neighbors:
        current_dv_matrix[n][n] = neighbors[n]

    prev_dv_matrix = [ [0, 0, 0, 0, 0],
                       [0, 0, 0, 0, 0],
                       [0, 0, 0, 0, 0],
                       [0, 0, 0, 0, 0],
                       [0, 0, 0, 0, 0]
                      ]



    sock = socket.socket(AF_INET, SOCK_STREAM)
    sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    server_address = ('127.0.0.1', 10500 + node_number)
    sock.bind(server_address)
    
    socket_for_node[node_number] = sock
    stop_threads = False
    listen_th = Thread(target=listen_thread, args=(lambda : stop_threads, node_number, current_dv_matrix,))
    listen_th.start()

    smth_changed_in_round = False

    while True:
        while dv_sender != node_number:
            if need_stop:
                break
            continue

        if need_stop:
            break

        updated = current_dv_matrix != prev_dv_matrix
        if updated:
            status = "Updated"
        else:
            status = "The same"

        sender_name = node_num_to_name(node_number)
        
        print("-------")
        print("Round %d: %s" % (current_round, sender_name))
        print("Current DV matrix = %s" % str(current_dv_matrix))
        print("Last DV matrix = %s" % str(prev_dv_matrix))
        print("Updated from last DV matrix or the same? %s" % status)

        if updated:
            for row in range(5):
                for col in range(5):
                    prev_dv_matrix[row][col] = current_dv_matrix[row][col]

            for neib in neighbors:
                message = str(node_number).encode('ascii')
                for m in range(5):
                    min_path = 999
                    
                    
                    for k in range(5):
                        if current_dv_matrix[m][k] < min_path:
                            min_path = current_dv_matrix[m][k]
                    message += (" " + str(m) + ":" + str(min_path)).encode('ascii')
                target_name = node_num_to_name(neib)
                print("%s Sending DV to node %s" % (sender_name, target_name))
                s = socket.socket(AF_INET, SOCK_STREAM)
                s.connect(('127.0.0.1', 10500 + neib))
                s.send(message)
                s.close()

        if dv_sender == 4:
            current_round += 1
            if not smth_changed_in_round:
                need_stop = True
                break
            dv_sender = 0
            smth_changed_in_round = False
        else:
            dv_sender += 1

    stop_threads = True
    listen_th.join()

    for target_node in [t for t in range(5) if t != node_number]:
        min_path = 999
        for column in range(5):
            if current_dv_matrix[target_node][column] < min_path:
                min_path = current_dv_matrix[target_node][column]
        shortest_paths.append((node_num_to_name(target_node), min_path))



def network_init():
    global current_round
    socket.setdefaulttimeout(1)


    adjaceny = [ [None, None, None, None, None],
                    [None, None, None, None, None],
                    [None, None, None, None, None],
                    [None, None, None, None, None],
                    [None, None, None, None, None]
                  ]
                  
    topology_file = open("network.txt")
    
    for line_num in range(5):
        line = topology_file.readline()
        numbers = line.split()
        for column_num in range(5):
            adjaceny[line_num][column_num] = int(numbers[column_num])
    topology_file.close()

    shortest_paths = [list(), list(), list(), list(), list()]
    thread_objs =  [None, None, None, None, None]
    for node_num in range(5):
        neighbors = {}
        
        for neighbor_num in range(5):
            if adjaceny[node_num][neighbor_num] > 0:
                neighbors[neighbor_num] = adjaceny[node_num][neighbor_num]


        thread_objs[node_num] = Thread(target=node_processor, 
                                        args=(node_num, neighbors, shortest_paths[node_num],)
                                    )
        thread_objs[node_num].start()

    thread_objs[0].join()
    thread_objs[1].join()
    thread_objs[2].join()
    thread_objs[3].join()
    thread_objs[4].join()


    print("-------")
    
    print("Final output:")
    print("Node A DV = %s" % str(shortest_paths[0]))
    print("Node B DV = %s" % str(shortest_paths[1]))
    print("Node C DV = %s" % str(shortest_paths[2]))
    print("Node D DV = %s" % str(shortest_paths[3]))
    print("Node E DV = %s" % str(shortest_paths[4]))
    print("Number of rounds till convergence (Round # when one of the nodes last updated its DV) = %d" % (current_round-1))

if __name__ == '__main__':
    network_init()
