def items(source, target, path: str = "$"):
    def recursive_compare(src, trg, curr_path):
        if type(src) is not type(trg):
            comp["modified"].append(curr_path)
            return
        if isinstance(src, dict):
            for key in src:
                if key not in trg:
                    comp["added"].append(f"{curr_path}.{key}")
                    continue
                recursive_compare(src[key], trg[key], f"{curr_path}.{key}")
            for key in trg:
                if key not in src:
                    comp["removed"].append(f"{curr_path}.{key}")
            return
        if isinstance(src, (list, tuple)):
            len_src = len(src)
            len_trg = len(trg)
            min_len = min(len_src, len_trg)
            for i in range(min_len):
                recursive_compare(src[i], trg[i], f"{curr_path}[{i}]")
            for i in range(min_len, max(len_src, len_trg)):
                comp["added" if len_src > len_trg else "removed"].append(f"{curr_path}[{i}]")
            return
        comp["unchanged" if src == trg else "modified"].append(curr_path)
        return
    comp = {"added": [], "removed": [], "modified": [], "unchanged": []}
    recursive_compare(source, target, path)
    return {key: sorted(comp[key]) for key in comp}
