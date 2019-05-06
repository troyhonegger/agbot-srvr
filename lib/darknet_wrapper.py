'''
This module allows us to run darknet on in-memory images, rather than writing an image to
disk and then reading it again using darknet. This should substantially speed up the process.

Admittedly, most of this is shamelessly copied off the Internet, with very minimal modifications.
Credits go to Glenn Jocher for a blog post with most of this code - find it online at
https://medium.com/@glenn.jocher/i-was-searching-for-a-fast-darknet-python-binding-also-but-found-what-i-needed-natively-within-the-11fcb76fe31e
'''

from darknet import *

def array_to_image(arr):
    arr = arr.transpose(2, 0, 1)
    c = arr.shape[0]
    h = arr.shape[1]
    w = arr.shape[2]
    arr = (arr / 255.0).flatten()
    data = c_array(c_float, arr)
    # I don't think darknet should change any of this. So we should be alright
    # without freeing im
    im = IMAGE(w, h, c, data)
    return im

def detect_cv2(net, meta, image, thresh=.5, hier_thresh=.5, nms=.45):
    if isinstance(image, bytes):  
        # image is a filename 
        # i.e. image = b'/darknet/data/dog.jpg'
        im = load_image(image, 0, 0)
    elif isinstance(image, str):
        im = load_image(image.encode('utf-8'), 0, 0)
    else:
        # image is a numpy array 
        # i.e. image = cv2.imread('/darknet/data/dog.jpg')
        im = array_to_image(image)
        rgbgr_image(im)
    
    num = c_int(0)
    pnum = pointer(num)
    predict_image(net, im)
    dets = get_network_boxes(net, im.w, im.h, thresh, 
                             hier_thresh, None, 0, pnum)
    num = pnum[0]
    if nms: do_nms_obj(dets, num, meta.classes, nms)
    
    res = []
    for j in range(num):
        for i in range(meta.classes):
            if dets[j].prob[i] > 0:
                b = dets[j].bbox
                res.append((meta.names[i], dets[j].prob[i], 
                           (b.x, b.y, b.w, b.h)))
    res = sorted(res, key=lambda x: -x[1])
    if isinstance(image, bytes) or isinstance(image, str): free_image(im)
    free_detections(dets, num)
    return res