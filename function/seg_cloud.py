import numpy as np
# import matplotlib.pyplot as plt
from skimage import io, color, filters, measure, morphology
from skimage.feature import graycomatrix, graycoprops
from sklearn.cluster import KMeans

# 加载图像
image_path = '6.jpg'
image = io.imread(image_path)  # 使用 skimage 加载图像，默认是 RGB 顺序

# 获取图像尺寸
height, width, _ = image.shape

# 转换为Lab颜色空间
image_lab = color.rgb2lab(image)

# 高斯平滑：对每个通道分别进行高斯平滑
for i in range(3):
    image_lab[:, :, i] = filters.gaussian(image_lab[:, :, i], sigma=1)

# 添加位置特征
x, y = np.meshgrid(np.arange(width), np.arange(height))
x = x / width
y = y / height

# 提取纹理特征
gray_image = color.rgb2gray(image)
glcm = graycomatrix((gray_image * 255).astype(np.uint8), distances=[5], angles=[0], symmetric=True, normed=True)
contrast = graycoprops(glcm, 'contrast').ravel()[0]
dissimilarity = graycoprops(glcm, 'dissimilarity').ravel()[0]
homogeneity = graycoprops(glcm, 'homogeneity').ravel()[0]
energy = graycoprops(glcm, 'energy').ravel()[0]
correlation = graycoprops(glcm, 'correlation').ravel()[0]
ASM = graycoprops(glcm, 'ASM').ravel()[0]

# 展平图像和位置特征以便于K-Means聚类
image_flatten = image_lab.reshape((-1, 3))
texture_features = np.tile([contrast, dissimilarity, homogeneity, energy, correlation, ASM], (image_flatten.shape[0], 1))
features = np.column_stack([image_flatten, x.ravel(), y.ravel(), texture_features])

# 使用K-Means进行颜色聚类
k = 5  # 增加聚类数量，以便更细致地分类
kmeans = KMeans(n_clusters=k, random_state=42).fit(features)
labels = kmeans.labels_
centers = kmeans.cluster_centers_

# 将聚类结果转换为图像
labels_image = labels.reshape(image.shape[:2])

# 为每个聚类标签分配明显的颜色
segmented_image = np.zeros_like(image)
colors = [
    [255, 0, 0],  # 红色
    [0, 255, 0],  # 绿色
    [0, 0, 255],  # 蓝色
    [255, 255, 0],  # 黄色
    [0, 255, 255],  # 青色
    [255, 0, 255],  # 洋红
    [128, 128, 128],  # 灰色
]

for i in range(k):
    segmented_image[labels_image == i] = colors[i % len(colors)]

# 根据Lab颜色空间和纹理特征选择天空类和地景类
# 使用位置特征进一步帮助区分
sky_label = np.argmax(centers[:, 3])
ground_label = np.argmin(centers[:, 0])

# 生成云朵和天空的掩码，同时排除地景
cloud_and_sky_mask = (labels != ground_label).reshape(image.shape[:2])
cloud_mask = (labels != sky_label) & (labels != ground_label)
cloud_mask = cloud_mask.reshape(image.shape[:2])

# 使用形态学操作去除小噪声
cloud_mask = morphology.remove_small_objects(cloud_mask, min_size=500)

# 计算云覆盖面积，减去地景部分
cloud_area = np.sum(cloud_mask)
total_area = np.sum(cloud_and_sky_mask)
cloud_coverage = cloud_area / total_area if total_area > 0 else 0

# 使用regionprops进行进一步分析
regions = measure.regionprops(cloud_mask.astype(int))
for region in regions:
    if region.area < 500:
        for coordinates in region.coords:
            cloud_mask[coordinates[0], coordinates[1]] = 0

# # 显示结果
# plt.figure(figsize=(15, 5))
# plt.subplot(1, 3, 1)
# plt.imshow(image)
# plt.title('Original Image')

# plt.subplot(1, 3, 2)
# plt.imshow(segmented_image)
# plt.title('Segmented Image')

# plt.subplot(1, 3, 3)
# plt.imshow(cloud_mask, cmap='gray')
# plt.title(f'Cloud Coverage: {cloud_coverage:.2%}')

# plt.show()

# # 保存结果图像
# io.imsave('segmented_image.png', segmented_image)
# io.imsave('cloud_mask.png', (cloud_mask * 255).astype(np.uint8))
