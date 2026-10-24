"""List the Kubernetes objects (kind, namespace, name) defined in manifest files.

Usage: python3 -m kst.inventory FILE...   (run from the repo clone)
Prints one tab-separated line per object: kind, namespace, name, file.

This is a line-based reader for the top level of each YAML document, not a full YAML
parser (the pipeline is standard library only). It reads `kind:` at column 0 and
`name:`/`namespace:` one level under `metadata:`; objects nested in a List are not listed.
"""
import re
import sys

DOC_SPLIT = re.compile(r"^---\s*$", re.M)
TOP_KEY = re.compile(r"^([A-Za-z]\w*):\s*(.*?)\s*$")
META_KEY = re.compile(r"^(\s+)(name|namespace):\s*(.*?)\s*$")

# Kinds that have no namespace. Kubernetes ignores a metadata.namespace on them, so we do too;
# otherwise a stray namespace that is later removed would split one object into two.
CLUSTER_SCOPED = frozenset({
    "APIService", "CSIDriver", "CertificateSigningRequest", "ClusterRole", "ClusterRoleBinding",
    "CustomResourceDefinition", "IngressClass", "MutatingWebhookConfiguration", "Namespace", "Node",
    "PersistentVolume", "PodSecurityPolicy", "PriorityClass", "RuntimeClass", "StorageClass",
    "ValidatingAdmissionPolicy", "ValidatingAdmissionPolicyBinding", "ValidatingWebhookConfiguration",
    "VolumeAttachment"})


def object_namespace(kind, namespace):
    return "" if kind in CLUSTER_SCOPED else namespace or ""


def _scalar(value):
    value = value.split(" #")[0].strip()
    return value.strip("'\"")


def objects(text):
    found = []
    for doc in DOC_SPLIT.split(text):
        kind, meta, in_meta, indent = None, {}, False, None
        for line in doc.splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            top = TOP_KEY.match(line)
            if top:
                in_meta = top.group(1) == "metadata"
                if top.group(1) == "kind":
                    kind = _scalar(top.group(2))
                continue
            if in_meta:
                m = META_KEY.match(line)
                depth = len(line) - len(line.lstrip())
                indent = depth if indent is None else indent
                if m and depth == indent and m.group(2) not in meta:
                    meta[m.group(2)] = _scalar(m.group(3))
        if kind:
            found.append((kind, object_namespace(kind, meta.get("namespace")), meta.get("name", "")))
    return found


def main(paths):
    for path in paths:
        with open(path, errors="replace") as f:
            for kind, namespace, name in objects(f.read()):
                print(f"{kind}\t{namespace}\t{name}\t{path}")


if __name__ == "__main__":
    main(sys.argv[1:])
