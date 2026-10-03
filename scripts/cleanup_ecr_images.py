#!/usr/bin/env python3
"""Empty exactly the four develop Bookinfo repositories after explicit operator confirmation."""
import argparse,json
from pathlib import Path

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inventory',required=True)
    a=p.parse_args()
    urls=json.loads(Path(a.inventory).read_text())
    expected={'devops-course-develop/'+s for s in ['productpage','details','ratings','reviews']}
    if not isinstance(urls,dict) or not all(isinstance(u,str) and '/' in u for u in urls.values()):
        raise SystemExit('Invalid inventory')
    names=[u.split('/',1)[1] for u in urls.values()]
    if len(names)!=4 or set(names)!=expected:raise SystemExit('Unexpected repositories; stop and inspect')
    import boto3
    session=boto3.Session();account=session.client('sts').get_caller_identity()['Account']
    registry=f"{account}.dkr.ecr.{session.region_name}.amazonaws.com"
    if any(u.split('/',1)[0]!=registry for u in urls.values()):raise SystemExit('Inventory does not match current AWS account/region')
    print('Account:',account,'Region:',session.region_name)
    print('Delete images from:');print('\n'.join(sorted(names)))
    if input('Type DELETE COURSE IMAGES to continue: ')!='DELETE COURSE IMAGES':raise SystemExit('Cancelled')
    c=session.client('ecr')
    for name in sorted(names):
        ids=[]
        for page in c.get_paginator('list_images').paginate(repositoryName=name):ids.extend(page['imageIds'])
        for i in range(0,len(ids),100):
            result=c.batch_delete_image(repositoryName=name,imageIds=ids[i:i+100])
            if result.get('failures'):raise RuntimeError(result['failures'])
        print('Emptied',name)
if __name__=='__main__':main()
