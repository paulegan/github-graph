#!/usr/bin/env python

import os
import logging
from argparse import ArgumentParser
from collections import namedtuple, defaultdict
from pickle import dump, load
from github import Github
import matplotlib.pyplot as plt
import numpy as np
import networkx as nx


# From http://colorbrewer2.org/?type=qualitative&scheme=Pastel2&n=6
COLORMAP = {'JavaScript': '#b3e2cd', 'CSS': '#cbd5e8'}


RepoMeta = namedtuple('RepoMeta', 'full_name size forks_count stargazers_count language')


def load_data(reponames, datafile, github_token=None, user_limit=None):
    if os.path.exists(datafile):
        with open(datafile, 'rb') as f:
            data = load(f)
    else:
        data = {}
        gh = Github(github_token)
        for reponame in reponames:
            weights, meta = defaultdict(int), dict()
            repo = gh.get_repo(reponame)
            user_count = 0
            for u in repo.get_stargazers():
                user_count += 1
                for r in u.get_starred():
                    weights[r.id] += 1
                    meta[r.id] = RepoMeta(*(getattr(r, f) for f in RepoMeta._fields))
                logging.info('users: %d	repos: %d', user_count, len(weights))
                if user_limit and user_count > user_limit:
                    break
            data[repo.id] = weights, meta
        # save for later
        with open(datafile, 'wb') as f:
            dump(data, f)

    return data


def create_graph(data, node_limit):
    g = nx.Graph()

    for repo_id, (weights, meta) in data.items():
        g.add_node(repo_id, root=True, **meta[repo_id]._asdict())

        for i, w in sorted(weights.items(), key=lambda x: x[1], reverse=True):
            if len(g[repo_id]) > node_limit:
                break
            logging.info('%-5d %-45s %-15s %d/%d', w, meta[i].full_name,
                         meta[i].language, meta[i].stargazers_count, meta[i].forks_count)
            if i != repo_id:
                g.add_node(i, meta[i]._asdict())
                g.add_edge(repo_id, i, weight=w)

    return g


def save_plot(g, plot_file):
    def normalize(x, min=0, max=1):
        x = np.asarray(x, float)
        d = x.max() - x.min()
        if d == 0:
            return x / x.min() * max
        else:
            return (x - x.min()) / d * (max - min) + min

    nodes, edges = g.nodes(data=True), g.edges(data=True)

    edgewidths = normalize([d['weight'] for u, v, d in edges], 1, 10)
    for (u, v, d), w in zip(edges, edgewidths):
        d['width'] = w

    nodesizes = normalize([d['stargazers_count'] for i, d in nodes], 100, 4000)
    nodecolors = [COLORMAP.get(d['language'], '#ffffff') for i, d in nodes]
    for (i, d), s, c in zip(nodes, nodesizes, nodecolors):
        d['size'], d['color'] = s, c

    rootlabels = {i: d['full_name'] for i, d in nodes if 'root' in d}
    labels = {i: d['full_name'] for i, d in nodes if 'root' not in d}

    pos = nx.spring_layout(g, k=0.9, iterations=100)
    nx.draw_networkx_edges(g, pos, width=edgewidths, alpha=0.05)
    nx.draw_networkx_nodes(g, pos, node_size=nodesizes, node_color=nodecolors, linewidths=0.01)
    nx.draw_networkx_labels(g, pos, labels, font_size=4)
    nx.draw_networkx_labels(g, pos, rootlabels, font_size=4, font_weight='bold')

    plt.axis('off')
    plt.savefig(plot_file, dpi=200)


if __name__ == '__main__':
    logging.basicConfig(format='%(message)s', level=logging.INFO)

    parser = ArgumentParser()
    parser.add_argument('--github-token')
    parser.add_argument('--user-limit', type=int, default=1000)
    parser.add_argument('--node-limit', type=int, default=40)
    parser.add_argument('--data-file', default='graph.data')
    parser.add_argument('--plot-file', default='graph.png')
    parser.add_argument('--json-file')
    parser.add_argument('initial_repos', nargs='+')
    args = parser.parse_args()

    data = load_data(args.initial_repos, args.data_file, args.github_token, args.user_limit)
    graph = create_graph(data, args.node_limit)
    save_plot(graph, args.plot_file)

    if args.json_file:
        from networkx.readwrite import json_graph
        import json
        with open(args.json_file, 'wt') as f:
            json.dump(json_graph.node_link_data(graph), f, indent=True)
