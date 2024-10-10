"""A Kubernetes Python Pulumi program"""

import pulumi
import pulumi_kubernetes as kubernetes
from pulumi_kubernetes.apps.v1 import Deployment
from pulumi_kubernetes.core.v1 import (
    Pod,
    PodSpecArgs,
    PersistentVolume,
    PersistentVolumeSpecArgs,
    PersistentVolumeClaim,
    PersistentVolumeClaimSpecArgs,
    PersistentVolumeClaimVolumeSourceArgs,
    NFSVolumeSourceArgs,
    CSIPersistentVolumeSourceArgs,
    VolumeArgs,
    ContainerArgs,
    ContainerPortArgs,
    SecurityContextArgs,
    VolumeMountArgs,
    VolumeArgsDict,
    VolumeResourceRequirementsArgs,
    EnvVarArgs,
)
from pulumi_kubernetes.meta.v1 import ObjectMetaArgs

pvc = PersistentVolumeClaim(
    "nfs-pvc",
    metadata=ObjectMetaArgs(name="my-nfs-pvc"),
    spec=PersistentVolumeClaimSpecArgs(
        # volume_name=pv.metadata.name,
        # persistent_volume_reclaim_policy="Retain",
        access_modes=["ReadWriteOnce"],
        resources=VolumeResourceRequirementsArgs(requests={"storage": "10Gi"}),
    ),
)

nfs_provisioner_service_account = kubernetes.core.v1.ServiceAccount(
    "nfs-provisioner",
    api_version="v1",
    kind="ServiceAccount",
    metadata={
        "annotations": {},
        "name": "nfs-provisioner",
        "namespace": "default",
    },
    opts=pulumi.ResourceOptions(protect=False),
)

nfs_provisioner_runner = kubernetes.rbac.v1.ClusterRole(
    "nfs-provisioner-runner",
    api_version="rbac.authorization.k8s.io/v1",
    kind="ClusterRole",
    metadata={
        "annotations": {},
        "name": "nfs-provisioner-runner",
    },
    rules=[
        {
            "api_groups": [""],
            "resources": ["persistentvolumes"],
            "verbs": [
                "get",
                "list",
                "watch",
                "create",
                "delete",
            ],
        },
        {
            "api_groups": [""],
            "resources": ["persistentvolumeclaims"],
            "verbs": [
                "get",
                "list",
                "watch",
                "update",
            ],
        },
        {
            "api_groups": ["storage.k8s.io"],
            "resources": ["storageclasses"],
            "verbs": [
                "get",
                "list",
                "watch",
            ],
        },
        {
            "api_groups": [""],
            "resources": ["events"],
            "verbs": [
                "create",
                "update",
                "patch",
            ],
        },
        {
            "api_groups": [""],
            "resources": [
                "services",
                "endpoints",
            ],
            "verbs": ["get"],
        },
        {
            "api_groups": ["extensions"],
            "resource_names": ["nfs-provisioner"],
            "resources": ["podsecuritypolicies"],
            "verbs": ["use"],
        },
    ],
    opts=pulumi.ResourceOptions(protect=False),
)

run_nfs_provisioner = kubernetes.rbac.v1.ClusterRoleBinding(
    "run-nfs-provisioner",
    api_version="rbac.authorization.k8s.io/v1",
    kind="ClusterRoleBinding",
    metadata={
        "annotations": {},
        "name": "run-nfs-provisioner",
    },
    role_ref={
        "api_group": "rbac.authorization.k8s.io",
        "kind": "ClusterRole",
        "name": "nfs-provisioner-runner",
    },
    subjects=[
        {
            "kind": "ServiceAccount",
            "name": "nfs-provisioner",
            "namespace": "default",
        }
    ],
    opts=pulumi.ResourceOptions(protect=False),
)

leader_locking_nfs_provisioner = kubernetes.rbac.v1.Role(
    "leader-locking-nfs-provisioner",
    api_version="rbac.authorization.k8s.io/v1",
    kind="Role",
    metadata={
        "annotations": {},
        "name": "leader-locking-nfs-provisioner",
        "namespace": "default",
    },
    rules=[
        {
            "api_groups": [""],
            "resources": ["endpoints"],
            "verbs": [
                "get",
                "list",
                "watch",
                "create",
                "update",
                "patch",
            ],
        }
    ],
    opts=pulumi.ResourceOptions(protect=False),
)

leader_locking_nfs_provisioner_role_binding = kubernetes.rbac.v1.RoleBinding(
    "leader-locking-nfs-provisioner",
    api_version="rbac.authorization.k8s.io/v1",
    kind="RoleBinding",
    metadata={
        "annotations": {},
        "name": "leader-locking-nfs-provisioner",
        "namespace": "default",
    },
    role_ref={
        "api_group": "rbac.authorization.k8s.io",
        "kind": "Role",
        "name": "leader-locking-nfs-provisioner",
    },
    subjects=[
        {
            "kind": "ServiceAccount",
            "name": "nfs-provisioner",
            "namespace": "default",
        }
    ],
    opts=pulumi.ResourceOptions(protect=False),
)

nfs_provisioner = kubernetes.apps.v1.Deployment(
    "nfs-provisioner",
    api_version="apps/v1",
    kind="Deployment",
    metadata={
        "annotations": {},
        "name": "nfs-provisioner",
        "namespace": "default",
    },
    spec={
        "progress_deadline_seconds": 600,
        "replicas": 1,
        "revision_history_limit": 10,
        "selector": {
            "match_labels": {
                "app": "nfs-provisioner",
            },
        },
        "strategy": {
            "type": "Recreate",
        },
        "template": {
            "metadata": {
                "labels": {
                    "app": "nfs-provisioner",
                },
            },
            "spec": {
                "containers": [
                    {
                        "args": ["-provisioner=example.com/nfs"],
                        "env": [
                            {
                                "name": "POD_IP",
                                "value_from": {
                                    "field_ref": {
                                        "api_version": "v1",
                                        "field_path": "status.podIP",
                                    },
                                },
                            },
                            {
                                "name": "SERVICE_NAME",
                                "value": "nfs-provisioner",
                            },
                            {
                                "name": "POD_NAMESPACE",
                                "value_from": {
                                    "field_ref": {
                                        "api_version": "v1",
                                        "field_path": "metadata.namespace",
                                    },
                                },
                            },
                        ],
                        "image": "registry.k8s.io/sig-storage/nfs-provisioner:v4.0.8",
                        "image_pull_policy": "IfNotPresent",
                        "name": "nfs-provisioner",
                        "ports": [
                            {
                                "container_port": 2049,
                                "name": "nfs",
                                "protocol": "TCP",
                            },
                            {
                                "container_port": 2049,
                                "name": "nfs-udp",
                                "protocol": "UDP",
                            },
                            {
                                "container_port": 32803,
                                "name": "nlockmgr",
                                "protocol": "TCP",
                            },
                            {
                                "container_port": 32803,
                                "name": "nlockmgr-udp",
                                "protocol": "UDP",
                            },
                            {
                                "container_port": 20048,
                                "name": "mountd",
                                "protocol": "TCP",
                            },
                            {
                                "container_port": 20048,
                                "name": "mountd-udp",
                                "protocol": "UDP",
                            },
                            {
                                "container_port": 875,
                                "name": "rquotad",
                                "protocol": "TCP",
                            },
                            {
                                "container_port": 875,
                                "name": "rquotad-udp",
                                "protocol": "UDP",
                            },
                            {
                                "container_port": 111,
                                "name": "rpcbind",
                                "protocol": "TCP",
                            },
                            {
                                "container_port": 111,
                                "name": "rpcbind-udp",
                                "protocol": "UDP",
                            },
                            {
                                "container_port": 662,
                                "name": "statd",
                                "protocol": "TCP",
                            },
                            {
                                "container_port": 662,
                                "name": "statd-udp",
                                "protocol": "UDP",
                            },
                        ],
                        "resources": {},
                        "security_context": {
                            "capabilities": {
                                "add": [
                                    "DAC_READ_SEARCH",
                                    "SYS_RESOURCE",
                                ],
                            },
                        },
                        "termination_message_path": "/dev/termination-log",
                        "termination_message_policy": "File",
                        "volume_mounts": [
                            {
                                "mount_path": "/export",
                                "name": "export-volume",
                            }
                        ],
                    }
                ],
                "dns_policy": "ClusterFirst",
                "restart_policy": "Always",
                "scheduler_name": "default-scheduler",
                "security_context": {},
                "service_account": "nfs-provisioner",
                "service_account_name": "nfs-provisioner",
                "termination_grace_period_seconds": 60,
                "volumes": [
                    {
                        "name": "export-volume",
                        "persistent_volume_claim": {"claim_name": pvc.metadata.name},
                    }
                ],
            },
        },
    },
    opts=pulumi.ResourceOptions(protect=False),
)

nfs_provisioner_service = kubernetes.core.v1.Service(
    "nfs-provisioner",
    api_version="v1",
    kind="Service",
    metadata={
        "annotations": {},
        "labels": {
            "app": "nfs-provisioner",
        },
        "name": "nfs-provisioner",
        "namespace": "default",
    },
    spec={
        "internal_traffic_policy": "Cluster",
        "ip_families": ["IPv4"],
        "ip_family_policy": "SingleStack",
        "ports": [
            {
                "name": "nfs",
                "port": 2049,
                "protocol": "TCP",
                "target_port": 2049,
            },
            {
                "name": "nfs-udp",
                "port": 2049,
                "protocol": "UDP",
                "target_port": 2049,
            },
            {
                "name": "nlockmgr",
                "port": 32803,
                "protocol": "TCP",
                "target_port": 32803,
            },
            {
                "name": "nlockmgr-udp",
                "port": 32803,
                "protocol": "UDP",
                "target_port": 32803,
            },
            {
                "name": "mountd",
                "port": 20048,
                "protocol": "TCP",
                "target_port": 20048,
            },
            {
                "name": "mountd-udp",
                "port": 20048,
                "protocol": "UDP",
                "target_port": 20048,
            },
            {
                "name": "rquotad",
                "port": 875,
                "protocol": "TCP",
                "target_port": 875,
            },
            {
                "name": "rquotad-udp",
                "port": 875,
                "protocol": "UDP",
                "target_port": 875,
            },
            {
                "name": "rpcbind",
                "port": 111,
                "protocol": "TCP",
                "target_port": 111,
            },
            {
                "name": "rpcbind-udp",
                "port": 111,
                "protocol": "UDP",
                "target_port": 111,
            },
            {
                "name": "statd",
                "port": 662,
                "protocol": "TCP",
                "target_port": 662,
            },
            {
                "name": "statd-udp",
                "port": 662,
                "protocol": "UDP",
                "target_port": 662,
            },
        ],
        "selector": {
            "app": "nfs-provisioner",
        },
        "session_affinity": "None",
        "type": kubernetes.core.v1.ServiceSpecType.CLUSTER_IP,
    },
    opts=pulumi.ResourceOptions(protect=False),
)
# nfs_server = Pod(
#     "nfs_server",
#     metadata=ObjectMetaArgs(name="nfs-server"),
#     spec=PodSpecArgs(
#         containers=[
#             ContainerArgs(
#                 name="nfs-server",
#                 image="ghcr.io/ntj125app/docker-nfs-server:nightly",
#                 security_context=SecurityContextArgs(
#                     privileged=True,
#                 ),
#                 env=[
#                     EnvVarArgs(
#                         name="NFS_EXPORT_0",
#                         value="/exports                  *(rw,no_subtree_check)",
#                     ),
#                 ],
#                 ports=[
#                     ContainerPortArgs(
#                         name="nfs",
#                         container_port=2049,
#                         protocol="TCP",
#                     ),
#                     ContainerPortArgs(
#                         name="mountd",
#                         container_port=20048,
#                         protocol="TCP",
#                     ),
#                     ContainerPortArgs(
#                         name="rpcbind",
#                         container_port=111,
#                         protocol="TCP",
#                     ),
#                 ],
#                 volume_mounts=[
#                     VolumeMountArgs(name="nfs-storage", mount_path="/exports")
#                 ],
#             ),
#         ],
#         volumes=[
#             VolumeArgs(
#                 name="nfs-storage",
#                 persistent_volume_claim=PersistentVolumeClaimVolumeSourceArgs(
#                     claim_name=pvc.metadata.name,
#                 ),
#             )
#         ],
#     ),
# )
