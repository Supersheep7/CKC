import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.colors as mcolors
import numpy as np

def restructure(graphs):
    
    '''
    Since I messed up in the graph factory we need a function 
    to restructure the graphs into a more usable format. 
    '''

    new_graphs = {}

    for size, topology_dict in graphs.items():
        new_graphs[size] = {}
        
        for topology, graph_or_dict in topology_dict.items():
            
            # Flatten: build a list of (topology_key, graph) pairs
            if isinstance(graph_or_dict, dict):  # Random, Scale-Free, Clustered
                items = [((topology, prob), g) for prob, g in graph_or_dict.items()]
            else:                                 # Wheel, Cycle
                items = [(topology, graph_or_dict)]
            
            for topo_key, g in items:
                new_graphs[size][topo_key] = {}
                first_node = list(g.nodes())[0]
                
                for n_s, tup_dict in g.nodes[first_node].items():
                    for tup, val_dict in tup_dict.items():
                        new_g = g.__class__()
                        new_g.add_nodes_from(g.nodes())
                        new_g.add_edges_from(g.edges())
                        new_g.graph['max_betas'] = n_s
                        new_g.graph['theories'] = tup
                        
                        for node in g.nodes():
                            attrs = {thresh: data['ab']
                                    for thresh, data in g.nodes[node][n_s][tup].items()}
                            nx.set_node_attributes(new_g, {node: attrs})
                        
                        new_graphs[size][topo_key].setdefault(n_s, {})[tup] = new_g
    return new_graphs

def debug_graphs(new_graphs):
    issues = []
    
    for size, topo_dict in new_graphs.items():
        for topo_key, ns_dict in topo_dict.items():
            for n_s, tup_dict in ns_dict.items():
                for tup, g in tup_dict.items():
                    nodes = list(g.nodes())
                    for node in nodes[:-1]:  # skip last node
                        attrs = g.nodes[node]
                        for thresh, ab in attrs.items():
                            if ab == 0 or ab is None:
                                issues.append({
                                    'size': size, 'topology': topo_key,
                                    'n_samples': n_s, 'tuple': tup,
                                    'node': node, 'threshold': thresh,
                                    'issue': 'zero or None ab'
                                })
                            elif any(v != v for v in ab):
                                issues.append({
                                    'size': size, 'topology': topo_key,
                                    'n_samples': n_s, 'tuple': tup,
                                    'node': node, 'threshold': thresh,
                                    'issue': 'NaN in ab'
                                })
    
    if issues:
        print(f"Found {len(issues)} issues:")
        for iss in issues:
            print(iss)
    else:
        print("All clean.")
    
    return issues


two_way_cmap = LinearSegmentedColormap.from_list('blue_black_yellow', ['#1f77b4', 'grey', '#ffdd00'])

def plot_graph(new_graphs, size, topology, density=None, top_prior_strength=None, theory_set=None, theory=None, cmap=two_way_cmap, max_certainty=None):
    
    topo_key = (topology, density) if density is not None else topology
    g = new_graphs[size][topo_key][top_prior_strength][theory_set]
    
    hub_nodes = [n for n in g.nodes() if not isinstance(g.nodes[n].get(theory), list)]
    regular_nodes = [n for n in g.nodes() if n not in hub_nodes]
    
    ev = {node: g.nodes[node][theory][0] / sum(g.nodes[node][theory]) 
          for node in regular_nodes}
    certainty = {node: sum(g.nodes[node][theory]) 
                 for node in regular_nodes}
    
    pos = nx.spring_layout(g, seed=42)
    fig, ax = plt.subplots(figsize=(8, 6))
    
    # Draw regular nodes
    nodes = nx.draw_networkx_nodes(g, pos, nodelist=regular_nodes,
                                    node_color=[ev[n] for n in regular_nodes],
                                    cmap=cmap, vmin=0, vmax=1, 
                                    node_size=600, ax=ax)
    
    log_certainty = {node: np.log(certainty[node]) for node in regular_nodes}
    min_lc = min(log_certainty.values()) 
    max_lc = max(log_certainty.values()) if max_certainty is None else np.log(max_certainty)
    linewidths = [0.5 + 4 * (log_certainty[n] - min_lc) / (max_lc - min_lc) for n in regular_nodes]
    nodes.set_linewidths(linewidths)
    nodes.set_edgecolors('black')

    # Draw hub nodes
    nx.draw_networkx_nodes(g, pos, nodelist=hub_nodes,
                            node_color='red', node_size=1200, ax=ax)
    
    # Deduplicate edges
    seen = set()
    unique_edges = []
    for u, v in g.edges():
        if (v, u) not in seen:
            unique_edges.append((u, v))
            seen.add((u, v))
    
    regular_edges = [e for e in unique_edges if e[0] not in hub_nodes and e[1] not in hub_nodes]
    hub_edges = [e for e in unique_edges if e[0] in hub_nodes or e[1] in hub_nodes]
    
    nx.draw_networkx_edges(g, pos, edgelist=regular_edges, alpha=0.3, arrows=False, ax=ax)
    nx.draw_networkx_edges(g, pos, edgelist=hub_edges, alpha=0.7, arrows=True, width=2.5, ax=ax)
    
    nx.draw_networkx_labels(g, pos, ax=ax)
    
    plt.colorbar(nodes, ax=ax, label=f'EV ({theory})')
    ax.set_title(f"n={size}, topology={topo_key}, top_prior_strength={top_prior_strength}, theory={theory}")
    plt.tight_layout()
    plt.show()


