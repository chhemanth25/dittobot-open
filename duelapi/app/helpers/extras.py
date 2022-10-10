from PIL import Image


def sresize(img):
    if img.height > img.width:
        baseheight = 380
        wpercent = baseheight / float(img.size[1])
        hsize = int((float(img.size[0]) * float(wpercent)))
        img = img.resize((hsize, baseheight), Image.ANTIALIAS)

    elif img.width > img.height:
        basewidth = 380
        wpercent = basewidth / float(img.size[0])
        hsize = int((float(img.size[1]) * float(wpercent)))
        img = img.resize((basewidth, hsize), Image.ANTIALIAS)

    return img
