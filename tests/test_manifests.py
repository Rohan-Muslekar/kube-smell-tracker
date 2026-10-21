from kst.manifests import skip_reason

DEPLOY = "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: web\n"


def test_plain_manifest_kept():
    assert skip_reason("deploy/web.yaml", DEPLOY) is None


def test_prometheus_rule_template_strings_kept():
    text = ("apiVersion: monitoring.coreos.com/v1\nkind: PrometheusRule\nspec:\n"
            "  groups:\n  - rules:\n    - annotations:\n"
            "        description: Pod {{ $labels.namespace }}/{{ $labels.pod }} is down\n")
    assert skip_reason("manifests/rule.yaml", text) is None


def test_go_template_in_comment_kept():
    text = "apiVersion: v1\nkind: ConfigMap\ndata:\n  _example: |\n    # {{.Name}} are also valid.\n"
    assert skip_reason("config/defaults.yaml", text) is None


def test_helm_template_skipped():
    text = "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: {{ include \"chart.fullname\" . }}\n"
    assert skip_reason("templates/deploy.yaml", text) == "templated"


def test_helm_values_reference_skipped():
    text = "apiVersion: v1\nkind: Service\nspec:\n  type: {{ .Values.service.type }}\n"
    assert skip_reason("templates/svc.yaml", text) == "templated"


def test_kustomization_skipped():
    text = "apiVersion: kustomize.config.k8s.io/v1beta1\nkind: Kustomization\nresources:\n- web.yaml\n"
    assert skip_reason("deploy/kustomization.yaml", text) == "kustomization"


def test_non_k8s_yaml_skipped():
    assert skip_reason("config/settings.yaml", "foo: bar\n") == "not a k8s object"


def test_prometheus_with_action_kept():
    text = ("apiVersion: monitoring.coreos.com/v1\nkind: PrometheusRule\nspec:\n  groups:\n  - rules:\n"
            "    - annotations:\n        description: PV in {{ $labels.namespace }} {{ with $labels.cluster -}} on {{ . }} {{- end }}\n")
    assert skip_reason("manifests/rule.yaml", text) is None
