Script to create a visualisation for a graph of Github repositories.

For a set of root repositories, the script discovers other associated 
projects by looking at each user who has starred the repo and then 
loading all other repos that user also starred. The resulting graph
is weighted by the number of starring users in common.


## To Run

    python github-graph.py --github-token xxx --plot-file testrepo.png --json-file testrepo.json github/testrepo
    display testrepo.png

    python -m SimpleHTTPServer &
    open 'http://localhost:8000/index.html?d=testrepo.json'
