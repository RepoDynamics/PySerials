import pyserials as ps
d = {
    "a1": {
        "b": {
            "c1": [1,2,3],
        },
    },
    "a2": "${{ a1.b.c1 }}"
}
ps.update.TemplateFiller(path_prefix="$.").fill("${{ a2[0] }}", d, always_list=False)