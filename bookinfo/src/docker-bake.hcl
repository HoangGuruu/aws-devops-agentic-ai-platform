group "default" {
  targets = ["productpage", "details", "ratings", "reviews"]
}
target "productpage" {
  context = "./productpage"
  tags = ["course/productpage:local"]
}
target "details" {
  context = "./details"
  tags = ["course/details:local"]
}
target "ratings" {
  context = "./ratings"
  tags = ["course/ratings:local"]
}
target "reviews" {
  context = "./reviews"
  tags = ["course/reviews:local"]
}
