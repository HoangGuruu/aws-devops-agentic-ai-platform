resource "aws_iam_role" "ebs" {
  count              = var.enable_storage ? 1 : 0
  name               = "${local.prefix}-ebs-csi"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Principal = { Service = "pods.eks.amazonaws.com" }, Action = ["sts:AssumeRole", "sts:TagSession"] }] })
}
resource "aws_iam_role_policy_attachment" "ebs" {
  count      = var.enable_storage ? 1 : 0
  role       = aws_iam_role.ebs[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy"
}
resource "aws_eks_pod_identity_association" "ebs" {
  count           = var.enable_storage ? 1 : 0
  cluster_name    = module.eks.name
  namespace       = "kube-system"
  service_account = "ebs-csi-controller-sa"
  role_arn        = aws_iam_role.ebs[0].arn
  depends_on      = [aws_eks_addon.pod_identity, aws_iam_role_policy_attachment.ebs]
}
resource "aws_eks_addon" "ebs" {
  count        = var.enable_storage ? 1 : 0
  cluster_name = module.eks.name
  addon_name   = "aws-ebs-csi-driver"
  depends_on   = [aws_eks_pod_identity_association.ebs]
}
resource "aws_iam_role" "load_balancer" {
  count              = var.enable_load_balancer_controller ? 1 : 0
  name               = "${local.prefix}-load-balancer-controller"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Principal = { Service = "pods.eks.amazonaws.com" }, Action = ["sts:AssumeRole", "sts:TagSession"] }] })
}
resource "aws_iam_role_policy" "load_balancer" {
  count  = var.enable_load_balancer_controller ? 1 : 0
  role   = aws_iam_role.load_balancer[0].id
  policy = file("${path.module}/../modules/eks/lb-controller-policy.json")
}
resource "aws_eks_pod_identity_association" "load_balancer" {
  count           = var.enable_load_balancer_controller ? 1 : 0
  cluster_name    = module.eks.name
  namespace       = "kube-system"
  service_account = "aws-load-balancer-controller"
  role_arn        = aws_iam_role.load_balancer[0].arn
  depends_on      = [aws_eks_addon.pod_identity, aws_iam_role_policy.load_balancer]
}
